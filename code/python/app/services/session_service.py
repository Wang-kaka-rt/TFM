from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings
from app.core.session_manager import SessionManager
from app.models.session import SessionInfo
from app.services.aggregator import NlpAggregator
from app.services.errors import SessionNotFoundError
from app.services.recorder import BaseRecorder, create_recorder
from app.services.refiner import BaseRefiner, create_refiner
from app.services.transcriber import BaseTranscriber, WordTiming, create_transcriber
from app.services.vad import BaseVoiceActivityDetector, create_vad

logger = logging.getLogger(__name__)


def _discover_ffmpeg_binary() -> Path | None:
    ffmpeg_env = os.environ.get("FFMPEG_BINARY")
    if ffmpeg_env and Path(ffmpeg_env).exists():
        return Path(ffmpeg_env)

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)

    bundled_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    candidates = (
        bundled_root / "assets" / "ffmpeg" / "ffmpeg.exe",
        bundled_root / "ffmpeg.exe",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


_FFMPEG_BINARY = _discover_ffmpeg_binary()
if _FFMPEG_BINARY is not None:
    os.environ.setdefault("FFMPEG_BINARY", str(_FFMPEG_BINARY))
    try:  # pragma: no cover - optional runtime dependency
        from pydub import AudioSegment  # type: ignore
    except ImportError:  # pragma: no cover - fallback path is covered
        AudioSegment = None
else:
    AudioSegment = None


@dataclass(slots=True)
class ChunkRecord:
    index: int
    audio_path: Path
    duration_seconds: float
    words: list[WordTiming] = field(default_factory=list)


@dataclass(slots=True)
class SessionRuntime:
    session_id: str
    workspace_dir: Path
    raw_dir: Path
    words_dir: Path
    phrases_dir: Path
    sentences_dir: Path
    metadata_path: Path
    samples_path: Path
    strudel_script_path: Path
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None
    chunks: list[ChunkRecord] = field(default_factory=list)


class SessionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._manager = SessionManager()
        self._effective_recorder_backend = settings.recorder_backend
        try:
            self._recorder = create_recorder(
                settings.recorder_backend,
                microphone_device=settings.microphone_device,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize recorder backend '%s' (%s); fallback to 'mock'.",
                settings.recorder_backend,
                exc,
            )
            self._recorder = create_recorder("mock", microphone_device=settings.microphone_device)
            self._effective_recorder_backend = "mock"

        self._effective_transcriber_backend = settings.transcriber_backend
        try:
            self._transcriber = create_transcriber(
                settings.transcriber_backend,
                settings.mock_transcript_words,
                faster_whisper_model=settings.faster_whisper_model,
                faster_whisper_device=settings.faster_whisper_device,
                faster_whisper_compute_type=settings.faster_whisper_compute_type,
                faster_whisper_beam_size=settings.faster_whisper_beam_size,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize transcriber backend '%s' (%s); fallback to 'mock'.",
                settings.transcriber_backend,
                exc,
            )
            self._transcriber = create_transcriber(
                "mock",
                settings.mock_transcript_words,
                faster_whisper_model=settings.faster_whisper_model,
                faster_whisper_device=settings.faster_whisper_device,
                faster_whisper_compute_type=settings.faster_whisper_compute_type,
                faster_whisper_beam_size=settings.faster_whisper_beam_size,
            )
            self._effective_transcriber_backend = "mock"

        self._vad: BaseVoiceActivityDetector = create_vad(
            settings.vad_backend,
            settings.min_word_duration_seconds,
        )
        self._aggregator = NlpAggregator(settings.phrase_group_size)
        self._refiner: BaseRefiner = create_refiner(settings.refinement_backend)
        self._runtimes: dict[str, SessionRuntime] = {}
        self._lock = asyncio.Lock()
        self._settings.samples_root.mkdir(parents=True, exist_ok=True)

    async def start(self, session_id: str) -> SessionInfo:
        async with self._lock:
            existing = self._runtimes.get(session_id)
            if existing is not None and existing.task is not None and not existing.task.done():
                return self._manager.require(session_id)

            runtime = self._build_runtime(session_id)
            self._reset_workspace(runtime)
            self._runtimes[session_id] = runtime

            session = self._manager.start(
                session_id,
                paths={
                    "workspace_dir": str(runtime.workspace_dir),
                    "raw_dir": str(runtime.raw_dir),
                    "words_dir": str(runtime.words_dir),
                    "phrases_dir": str(runtime.phrases_dir),
                    "sentences_dir": str(runtime.sentences_dir),
                    "metadata_path": str(runtime.metadata_path),
                    "samples_path": str(runtime.samples_path),
                    "strudel_script_path": str(runtime.strudel_script_path),
                },
            )
            runtime.task = asyncio.create_task(self._record_session(runtime))
            runtime.task.add_done_callback(lambda task: self._handle_runtime_task_done(runtime, task))
            return session

    async def stop(self, session_id: str) -> SessionInfo:
        runtime = self._require_runtime(session_id)
        runtime.stop_event.set()
        if runtime.task is not None:
            try:
                await runtime.task
            except asyncio.CancelledError:
                logger.warning("Session task was cancelled before stop: %s", session_id)
        self._manager.set_processing(session_id, event="finalizing")
        if self._settings.enable_refinement:
            await asyncio.to_thread(self._refine_runtime_words, runtime)
        self._write_artifacts(runtime)
        return self._manager.stop(session_id)

    async def reload(self, session_id: str) -> SessionInfo:
        runtime = self._require_runtime(session_id)
        if runtime.task is not None and not runtime.task.done():
            runtime.stop_event.set()
            try:
                await runtime.task
            except asyncio.CancelledError:
                logger.warning("Session task was cancelled before reload: %s", session_id)
        self._manager.set_processing(session_id, event="rebuilding-artifacts")
        if self._settings.enable_refinement:
            await asyncio.to_thread(self._refine_runtime_words, runtime)
        self._write_artifacts(runtime)
        return self._manager.reload(session_id)

    def get(self, session_id: str) -> SessionInfo | None:
        return self._manager.get(session_id)

    def active(self) -> SessionInfo | None:
        return self._manager.active()

    def all(self) -> list[SessionInfo]:
        return self._manager.all()

    def get_strudel_script_path(self, session_id: str) -> Path:
        runtime = self._require_runtime(session_id)
        return runtime.strudel_script_path

    def get_samples_manifest_path(self, session_id: str) -> Path:
        runtime = self._require_runtime(session_id)
        return runtime.samples_path

    def get_metadata_path(self, session_id: str) -> Path:
        runtime = self._require_runtime(session_id)
        return runtime.metadata_path

    def get_metrics(self) -> dict[str, int]:
        sessions = self._manager.all()
        return {
            "session_count": len(sessions),
            "active_session_count": 0 if self._manager.active() is None else 1,
            "total_chunks": sum(item.chunk_count for item in sessions),
            "total_words": sum(item.word_count for item in sessions),
            "total_phrases": sum(item.phrase_count for item in sessions),
            "total_sentences": sum(item.sentence_count for item in sessions),
        }

    async def _record_session(self, runtime: SessionRuntime) -> None:
        try:
            for chunk_index in range(1, self._settings.max_chunks_per_session + 1):
                if runtime.stop_event.is_set():
                    break

                file_name = f"{self._settings.mock_chunk_prefix}_{chunk_index:04d}.wav"
                audio_path = runtime.raw_dir / file_name
                audio_info = await asyncio.to_thread(
                    self._recorder.record_chunk,
                    audio_path,
                    duration_seconds=self._settings.chunk_duration_seconds,
                    sample_rate=self._settings.sample_rate,
                    channels=self._settings.channels,
                    chunk_index=chunk_index,
                )
                words = await asyncio.to_thread(
                    self._transcriber.transcribe,
                    audio_path,
                    chunk_index=chunk_index,
                )
                if self._settings.enable_vad:
                    words = self._vad.filter_words(words)
                chunk = ChunkRecord(
                    index=chunk_index,
                    audio_path=audio_path,
                    duration_seconds=audio_info.duration_seconds,
                    words=words,
                )
                runtime.chunks.append(chunk)
                self._export_word_samples(runtime, chunk)
                self._write_artifacts(runtime)
                await asyncio.sleep(self._settings.session_poll_interval_seconds)

            self._write_artifacts(runtime)
        except Exception as exc:  # pragma: no cover - runtime protection
            self._manager.fail(runtime.session_id, str(exc))
            raise

    def _build_runtime(self, session_id: str) -> SessionRuntime:
        workspace_dir = self._settings.samples_root / session_id
        return SessionRuntime(
            session_id=session_id,
            workspace_dir=workspace_dir,
            raw_dir=workspace_dir / "raw",
            words_dir=workspace_dir / "words",
            phrases_dir=workspace_dir / "phrases",
            sentences_dir=workspace_dir / "sentences",
            metadata_path=workspace_dir / "metadata.json",
            samples_path=workspace_dir / "samples.json",
            strudel_script_path=workspace_dir / "strudel.js",
        )

    def _reset_workspace(self, runtime: SessionRuntime) -> None:
        if runtime.workspace_dir.exists():
            shutil.rmtree(runtime.workspace_dir, ignore_errors=True)
        runtime.raw_dir.mkdir(parents=True, exist_ok=True)
        runtime.words_dir.mkdir(parents=True, exist_ok=True)
        runtime.phrases_dir.mkdir(parents=True, exist_ok=True)
        runtime.sentences_dir.mkdir(parents=True, exist_ok=True)
        runtime.chunks.clear()
        runtime.stop_event = asyncio.Event()
        runtime.task = None

    def _export_word_samples(self, runtime: SessionRuntime, chunk: ChunkRecord) -> None:
        for word_index, word in enumerate(chunk.words, start=1):
            word_file = runtime.words_dir / f"word_{chunk.index:04d}_{word_index:02d}_{word.word}.wav"
            export_wav_slice(chunk.audio_path, word_file, word.start, word.end)

    def _write_artifacts(self, runtime: SessionRuntime) -> None:
        word_samples = self._collect_word_samples(runtime)
        phrase_samples = self._collect_phrase_samples(runtime)
        sentence_samples = self._collect_sentence_samples(runtime)

        metadata = {
            "session_id": runtime.session_id,
            "chunk_duration_seconds": self._settings.chunk_duration_seconds,
            "sample_rate": self._settings.sample_rate,
            "channels": self._settings.channels,
            "recorder_backend": self._effective_recorder_backend,
            "transcriber_backend": self._effective_transcriber_backend,
            "vad_backend": self._settings.vad_backend if self._settings.enable_vad else "disabled",
            "refinement_backend": self._settings.refinement_backend if self._settings.enable_refinement else "disabled",
            "chunks": [
                {
                    "index": chunk.index,
                    "audio_file": chunk.audio_path.name,
                    "audio_path": str(chunk.audio_path),
                    "duration_seconds": chunk.duration_seconds,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                        }
                        for word in chunk.words
                    ],
                }
                for chunk in runtime.chunks
            ],
        }
        runtime.metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        samples = {
            "session_id": runtime.session_id,
            "base_url": f"{self._settings.strudel_base_url}/samples/{runtime.session_id}",
            "words": word_samples,
            "phrases": phrase_samples,
            "sentences": sentence_samples,
        }
        runtime.samples_path.write_text(
            json.dumps(samples, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        script = build_strudel_script(
            session_id=runtime.session_id,
            base_url=self._settings.strudel_base_url,
            word_samples=word_samples,
            phrase_samples=phrase_samples,
            sentence_samples=sentence_samples,
        )
        runtime.strudel_script_path.write_text(script, encoding="utf-8")

        self._manager.update_counts(
            runtime.session_id,
            chunk_count=len(runtime.chunks),
            word_count=len(word_samples),
            phrase_count=len(phrase_samples),
            sentence_count=len(sentence_samples),
        )

    def _collect_word_samples(self, runtime: SessionRuntime) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for chunk in runtime.chunks:
            for word_index, word in enumerate(chunk.words, start=1):
                file_name = f"word_{chunk.index:04d}_{word_index:02d}_{word.word}.wav"
                items.append(
                    {
                        "name": f"{word.word}_{chunk.index:04d}_{word_index:02d}",
                        "text": word.word,
                        "level": "word",
                        "chunk_index": chunk.index,
                        "start": word.start,
                        "end": word.end,
                        "duration_seconds": round(word.end - word.start, 3),
                        "path": f"words/{file_name}",
                        "url": f"{self._settings.strudel_base_url}/samples/{runtime.session_id}/words/{file_name}",
                    }
                )
        return items

    def _refine_runtime_words(self, runtime: SessionRuntime) -> None:
        for chunk in runtime.chunks:
            refined = self._refiner.refine(chunk.audio_path, chunk.words)
            chunk.words = refined if refined else chunk.words

    def _collect_phrase_samples(self, runtime: SessionRuntime) -> list[dict[str, object]]:
        if not self._settings.enable_phrase_and_sentence_exports:
            return []

        items: list[dict[str, object]] = []
        for chunk in runtime.chunks:
            for phrase in self._aggregator.to_phrases(chunk.words):
                phrase_index = len(items) + 1
                text = "_".join(phrase.words)
                file_name = f"phrase_{phrase_index:04d}_{text}.wav"
                export_wav_slice(chunk.audio_path, runtime.phrases_dir / file_name, phrase.start, phrase.end)
                items.append(
                    {
                        "name": f"phrase_{phrase_index:04d}",
                        "text": phrase.text,
                        "level": "phrase",
                        "chunk_index": chunk.index,
                        "start": phrase.start,
                        "end": phrase.end,
                        "duration_seconds": round(phrase.end - phrase.start, 3),
                        "path": f"phrases/{file_name}",
                        "url": f"{self._settings.strudel_base_url}/samples/{runtime.session_id}/phrases/{file_name}",
                    }
                )
        return items

    def _collect_sentence_samples(self, runtime: SessionRuntime) -> list[dict[str, object]]:
        if not self._settings.enable_phrase_and_sentence_exports:
            return []

        items: list[dict[str, object]] = []
        for chunk in runtime.chunks:
            sentence = self._aggregator.to_sentence(chunk.words)
            if sentence is None:
                continue
            file_name = f"sentence_{chunk.index:04d}.wav"
            export_wav_slice(chunk.audio_path, runtime.sentences_dir / file_name, sentence.start, sentence.end)
            items.append(
                {
                    "name": f"sentence_{chunk.index:04d}",
                    "text": sentence.text,
                    "level": "sentence",
                    "chunk_index": chunk.index,
                    "start": sentence.start,
                    "end": sentence.end,
                    "duration_seconds": round(sentence.end - sentence.start, 3),
                    "path": f"sentences/{file_name}",
                    "url": f"{self._settings.strudel_base_url}/samples/{runtime.session_id}/sentences/{file_name}",
                }
            )
        return items

    def _require_runtime(self, session_id: str) -> SessionRuntime:
        runtime = self._runtimes.get(session_id)
        if runtime is None:
            raise SessionNotFoundError(session_id)
        return runtime

    def _handle_runtime_task_done(self, runtime: SessionRuntime, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exception = task.exception()
        if exception is None:
            return
        logger.error(
            "Session task failed for %s",
            runtime.session_id,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        self._manager.fail(runtime.session_id, str(exception))


def export_wav_slice(source_path: Path, target_path: Path, start_seconds: float, end_seconds: float) -> None:
    if AudioSegment is not None:
        segment = AudioSegment.from_file(source_path)
        clip = segment[int(max(0.0, start_seconds) * 1000) : int(max(start_seconds + 0.001, end_seconds) * 1000)]
        clip.export(target_path, format="wav")
        return

    with wave.open(str(source_path), "rb") as source:
        sample_rate = source.getframerate()
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        start_frame = max(0, int(start_seconds * sample_rate))
        end_frame = max(start_frame + 1, int(end_seconds * sample_rate))
        source.setpos(min(start_frame, source.getnframes()))
        frame_count = max(1, min(end_frame, source.getnframes()) - start_frame)
        frames = source.readframes(frame_count)

    with wave.open(str(target_path), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(sample_width)
        target.setframerate(sample_rate)
        target.writeframes(frames)


def build_strudel_script(
    *,
    session_id: str,
    base_url: str,
    word_samples: list[dict[str, object]],
    phrase_samples: list[dict[str, object]],
    sentence_samples: list[dict[str, object]],
) -> str:
    payload = {
        "sessionId": session_id,
        "samples": {
            "words": word_samples,
            "phrases": phrase_samples,
            "sentences": sentence_samples,
        },
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        f"const STRUDEL_VOICE = {data};\n\n"
        f"export const strudelVoiceSession = STRUDEL_VOICE.sessionId;\n"
        f"export const strudelVoiceSamples = STRUDEL_VOICE.samples;\n"
        f"export async function start(sessionId) {{\n"
        f"  const response = await fetch('{base_url}/start', {{\n"
        f"    method: 'POST',\n"
        f"    headers: {{ 'Content-Type': 'application/json' }},\n"
        f"    body: JSON.stringify({{ session_id: sessionId }}),\n"
        f"  }});\n"
        f"  return response.json();\n"
        f"}}\n"
        f"export async function reload(sessionId) {{\n"
        f"  const response = await fetch('{base_url}/reload', {{\n"
        f"    method: 'POST',\n"
        f"    headers: {{ 'Content-Type': 'application/json' }},\n"
        f"    body: JSON.stringify({{ session_id: sessionId }}),\n"
        f"  }});\n"
        f"  return response.json();\n"
        f"}}\n"
        f"export async function stop(sessionId) {{\n"
        f"  const response = await fetch('{base_url}/stop', {{\n"
        f"    method: 'POST',\n"
        f"    headers: {{ 'Content-Type': 'application/json' }},\n"
        f"    body: JSON.stringify({{ session_id: sessionId }}),\n"
        f"  }});\n"
        f"  return response.json();\n"
        f"}}\n"
    )
