from __future__ import annotations

import logging
import os
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
STARTUP_RETRIES = 3
STARTUP_TIMEOUT_SECONDS = 12.0


def resolve_runtime_root() -> Path:
    # PyInstaller one-file mode extracts files to _MEIPASS.
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[1]


def resolve_logs_dir() -> Path:
    local_app_data = Path.home() / "AppData" / "Local"
    logs_dir = local_app_data / "StrudelVoice" / "logs"
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
    bundled_candidates = (
        runtime_root / "assets" / "ffmpeg" / "ffmpeg.exe",
        runtime_root / "ffmpeg.exe",
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
    if ffmpeg_dir not in current_path:
        os.environ["PATH"] = f"{ffmpeg_dir};{current_path}" if current_path else ffmpeg_dir
    os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
    os.environ["IMAGEIO_FFMPEG_EXE"] = str(ffmpeg_path)
    safe_log(logger, "info", "Configured FFmpeg executable: %s", ffmpeg_path)


def main() -> None:
    logger, _ = setup_logging()
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    base_url = f"http://{host}:{port}"
    runtime_root = resolve_runtime_root()
    configure_ffmpeg_environment(runtime_root, logger)

    safe_log(logger, "info", "Launcher started. runtime_root=%s", runtime_root)
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

        import webview  # type: ignore

        default_session_id = os.environ.get("STRUDEL_SESSION_ID", "demo01")
        startup_url = (
            f"{base_url}/index.html?svSession={quote(default_session_id, safe='')}"
            f"&svBase={quote(base_url, safe='')}"
        )
        webview.create_window("Strudel Voice", startup_url, width=1200, height=800)
        safe_log(logger, "info", "Opening desktop window at %s", startup_url)
        webview.start()
    finally:
        safe_log(logger, "info", "Launcher exited.")


if __name__ == "__main__":
    main()
