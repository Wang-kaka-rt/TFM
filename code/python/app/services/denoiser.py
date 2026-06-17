from __future__ import annotations

import wave
from pathlib import Path


class BaseDenoiser:
    """Reduce background noise of a recorded chunk before transcription.

    Implementations operate on a WAV file in place: they read ``audio_path`` and,
    when they successfully produce a cleaned signal, overwrite the same file so
    the rest of the pipeline (transcription + slicing) works on denoised audio.
    A denoiser must never raise: on any failure it leaves the file untouched.
    """

    def denoise(self, audio_path: Path) -> bool:
        raise NotImplementedError


class NullDenoiser(BaseDenoiser):
    """No-op denoiser used by default and for the mock pipeline."""

    def denoise(self, audio_path: Path) -> bool:
        return False


class NoiseReduceDenoiser(BaseDenoiser):
    """Spectral-gating denoiser backed by the ``noisereduce`` library.

    Good for stationary background noise (fans, air conditioning, line hum).
    The dependency is optional; if it is missing the denoiser silently degrades
    to a no-op so the service keeps running.
    """

    def __init__(self, *, prop_decrease: float = 0.8, stationary: bool = False) -> None:
        self._prop_decrease = max(0.0, min(1.0, prop_decrease))
        # Non-stationary mode tracks time-varying noise and preserves the voiced
        # signal far better than stationary mode (verified empirically), so it is
        # the default. Stationary mode suits a constant hum but over-attenuates.
        self._stationary = stationary
        self._available = False
        self._nr = None
        self._np = None
        try:
            import noisereduce as nr  # type: ignore
            import numpy as np  # type: ignore

            self._nr = nr
            self._np = np
            self._available = True
        except ImportError:
            self._available = False

    def denoise(self, audio_path: Path) -> bool:
        if not self._available or self._nr is None or self._np is None:
            return False
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())

            if sample_width != 2 or not frames:
                # Only 16-bit PCM is handled; leave anything else untouched.
                return False

            np = self._np
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                audio = audio.reshape(-1, channels).mean(axis=1)

            reduced = self._nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                prop_decrease=self._prop_decrease,
                stationary=self._stationary,
            )

            cleaned = np.clip(reduced, -1.0, 1.0)
            pcm = (cleaned * 32767.0).astype(np.int16).tobytes()
            with wave.open(str(audio_path), "wb") as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(2)
                wav_out.setframerate(sample_rate)
                wav_out.writeframes(pcm)
            return True
        except Exception:
            return False


def create_denoiser(
    backend: str,
    *,
    prop_decrease: float = 0.8,
    stationary: bool = False,
) -> BaseDenoiser:
    if backend == "noisereduce":
        return NoiseReduceDenoiser(prop_decrease=prop_decrease, stationary=stationary)
    return NullDenoiser()
