from __future__ import annotations

import logging
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
import platform
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from app.services.panel import control_panel_script

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
STARTUP_RETRIES = 3
STARTUP_TIMEOUT_SECONDS = 90.0
UI_INJECTION_TIMEOUT_SECONDS = 20.0


def resolve_runtime_root() -> Path:
    # PyInstaller one-file mode extracts files to _MEIPASS.
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[1]


def resolve_logs_dir() -> Path:
    if sys.platform == "win32":
        logs_dir = Path.home() / "AppData" / "Local" / "StrudelVoice" / "logs"
    elif sys.platform == "darwin":
        logs_dir = Path.home() / "Library" / "Application Support" / "StrudelVoice" / "logs"
    else:
        logs_dir = Path.home() / ".local" / "share" / "strudel-voice" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def setup_logging() -> tuple[logging.Logger, Path]:
    logs_dir = resolve_logs_dir()
    launcher_log_path = logs_dir / "launcher.log"
    logging.raiseExceptions = False
    logger = logging.getLogger("strudel.launcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    file_handler = logging.FileHandler(launcher_log_path, encoding="utf-8", delay=True)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger, logs_dir


def safe_log(logger: logging.Logger, level: str, message: str, *args, **kwargs) -> None:
    try:
        getattr(logger, level)(message, *args, **kwargs)
    except Exception:
        # Avoid surfacing logging handler errors to end users in frozen EXE mode.
        pass


def ensure_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex((host, port)) == 0:
            raise RuntimeError(f"Port {port} is already in use.")


def healthcheck(base_url: str) -> bool:
    try:
        with urlopen(f"{base_url}/health", timeout=1.5) as response:
            return response.status == 200
    except (URLError, TimeoutError):
        return False


def wait_backend(host: str, port: int, timeout_seconds: float = STARTUP_TIMEOUT_SECONDS) -> None:
    started = time.time()
    while time.time() - started < timeout_seconds:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError("Backend did not start in time.")


def resolve_ffmpeg_path(runtime_root: Path) -> Path | None:
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    bundled_candidates = (
        runtime_root / "assets" / "ffmpeg" / ffmpeg_exe,
        runtime_root / ffmpeg_exe,
    )
    for candidate in bundled_candidates:
        if candidate.exists():
            return candidate
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)
    return None


def configure_ffmpeg_environment(runtime_root: Path, logger: logging.Logger) -> None:
    ffmpeg_path = resolve_ffmpeg_path(runtime_root)
    if ffmpeg_path is None:
        safe_log(logger, "warning", "FFmpeg executable not found; pydub may show warnings.")
        return

    ffmpeg_dir = str(ffmpeg_path.parent)
    current_path = os.environ.get("PATH", "")
    path_sep = ";" if sys.platform == "win32" else ":"
    if ffmpeg_dir not in current_path:
        os.environ["PATH"] = f"{ffmpeg_dir}{path_sep}{current_path}" if current_path else ffmpeg_dir
    os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
    os.environ["IMAGEIO_FFMPEG_EXE"] = str(ffmpeg_path)
    safe_log(logger, "info", "Configured FFmpeg executable: %s", ffmpeg_path)


def configure_runtime_defaults(logger: logging.Logger) -> None:
    if sys.platform == "win32":
        default_samples_root = Path.home() / "Documents" / "StrudelVoice" / "samples"
    else:
        default_samples_root = Path.home() / "Documents" / "strudel-voice" / "samples"
    machine_name = platform.machine().lower()
    is_windows_arm = sys.platform == "win32" and machine_name in {"arm64", "aarch64"}
    # Windows-on-ARM still lacks a reliable bundled PortAudio build, so it keeps the
    # browser capture path. Linux records server-side via sounddevice/PortAudio so the
    # captured audio is real (the browser path silently produced empty/silent chunks
    # on many Ubuntu setups). Requires libportaudio2 to be installed on the system.
    default_recorder_backend = "browser" if is_windows_arm else "microphone"
    defaults = {
        "STRUDEL_RECORDER_BACKEND": default_recorder_backend,
        "STRUDEL_TRANSCRIBER_BACKEND": "faster-whisper",
        # Use the medium model for better accuracy on fast/colloquial speech. device
        # and compute_type are "auto": on an NVIDIA GPU this runs on CUDA with float16,
        # and on a CPU-only machine it falls back to CPU with int8 automatically.
        "STRUDEL_FASTER_WHISPER_MODEL": "medium",
        "STRUDEL_FASTER_WHISPER_DEVICE": "auto",
        "STRUDEL_FASTER_WHISPER_COMPUTE_TYPE": "auto",
        "STRUDEL_VAD_BACKEND": "silero",
        "STRUDEL_ENABLE_VAD": "true",
        "STRUDEL_SAMPLES_ROOT": str(default_samples_root),
        "STRUDEL_CHUNK_DURATION_SECONDS": "1.5" if is_windows_arm else "2.5",
    }
    bundled_models = resolve_runtime_root() / "assets" / "models"
    if bundled_models.is_dir():
        defaults["STRUDEL_FASTER_WHISPER_DOWNLOAD_ROOT"] = str(bundled_models)
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    safe_log(
        logger,
        "info",
        "Runtime defaults recorder=%s transcriber=%s vad=%s chunk=%s machine=%s",
        os.environ.get("STRUDEL_RECORDER_BACKEND"),
        os.environ.get("STRUDEL_TRANSCRIBER_BACKEND"),
        os.environ.get("STRUDEL_VAD_BACKEND"),
        os.environ.get("STRUDEL_CHUNK_DURATION_SECONDS"),
        machine_name,
    )


def main() -> None:
    logger, _ = setup_logging()
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    base_url = f"http://{host}:{port}"
    runtime_root = resolve_runtime_root()
    configure_ffmpeg_environment(runtime_root, logger)
    configure_runtime_defaults(logger)

    safe_log(logger, "info", "Launcher started. runtime_root=%s platform=%s", runtime_root, sys.platform)
    backend_error: dict[str, Exception | None] = {"error": None}

    def start_backend() -> None:
        try:
            from uvicorn import run  # type: ignore

            run("app.main:app", host=host, port=port)
        except Exception as exc:  # pragma: no cover - runtime protection
            backend_error["error"] = exc
            safe_log(logger, "exception", "Backend crashed")

    def wait_backend_ready(timeout_seconds: float = STARTUP_TIMEOUT_SECONDS) -> None:
        started = time.time()
        while time.time() - started < timeout_seconds:
            if backend_error["error"] is not None:
                raise RuntimeError(f"Backend startup failed: {backend_error['error']}")
            if healthcheck(base_url):
                return
            time.sleep(0.2)
        raise RuntimeError("Backend did not become healthy in time.")

    try:
        if healthcheck(base_url):
            safe_log(logger, "info", "Existing backend is healthy at %s", base_url)
        else:
            ensure_port_available(host, port)
            for attempt in range(1, STARTUP_RETRIES + 1):
                safe_log(logger, "info", "Starting backend attempt=%s", attempt)
                backend_error["error"] = None
                thread = threading.Thread(target=start_backend, daemon=True)
                thread.start()
                try:
                    wait_backend_ready()
                    safe_log(logger, "info", "Backend started successfully at %s", base_url)
                    break
                except Exception as exc:
                    safe_log(logger, "exception", "Backend startup attempt %s failed", attempt)
                    time.sleep(0.5 * attempt)
            else:
                raise RuntimeError(
                    f"Backend failed after {STARTUP_RETRIES} retries. "
                    "See launcher.log for details."
                )

        default_session_id = os.environ.get("STRUDEL_SESSION_ID", "demo01")
        startup_url = (
            f"{base_url}/index.html?svSession={quote(default_session_id, safe='')}"
            f"&svBase={quote(base_url, safe='')}"
        )

        if sys.platform == "win32":
            # Windows: embedded WebView window. The control panel is also injected
            # via HTML by routes.py, but we call evaluate_js as an extra guarantee
            # in case the page was cached before injection was added.
            import webview  # type: ignore

            window = webview.create_window("Strudel Voice", startup_url, width=1200, height=800)
            safe_log(logger, "info", "Opening desktop window at %s", startup_url)

            def inject_control_panel(window_obj) -> None:
                script = control_panel_script(default_session_id)
                deadline = time.time() + UI_INJECTION_TIMEOUT_SECONDS
                while time.time() < deadline:
                    try:
                        ready_state = window_obj.evaluate_js("document.readyState")
                        if ready_state in ("interactive", "complete"):
                            window_obj.evaluate_js(script)
                            safe_log(logger, "info", "Voice control panel injected via evaluate_js.")
                            return
                    except Exception:
                        # Window may not be ready yet.
                        pass
                    time.sleep(0.25)
                safe_log(logger, "warning", "Voice control panel injection timed out.")

            webview.start(inject_control_panel, window)

        else:
            # Linux / macOS: open the system browser. The control panel is injected
            # automatically by the backend's HTML endpoint (routes.py), so no
            # additional JS injection is needed here.
            safe_log(logger, "info", "Opening system browser at %s", startup_url)
            webbrowser.open(startup_url)
            safe_log(logger, "info", "Backend running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                safe_log(logger, "info", "Interrupted by user.")

    finally:
        safe_log(logger, "info", "Launcher exited.")


if __name__ == "__main__":
    main()
