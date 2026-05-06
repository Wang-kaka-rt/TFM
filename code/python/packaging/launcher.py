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
STARTUP_TIMEOUT_SECONDS = 90.0
UI_INJECTION_TIMEOUT_SECONDS = 20.0


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


def configure_runtime_defaults(logger: logging.Logger) -> None:
    default_samples_root = Path.home() / "Documents" / "StrudelVoice" / "samples"
    defaults = {
        "STRUDEL_RECORDER_BACKEND": "microphone",
        "STRUDEL_TRANSCRIBER_BACKEND": "faster-whisper",
        "STRUDEL_VAD_BACKEND": "silero",
        "STRUDEL_ENABLE_VAD": "true",
        "STRUDEL_SAMPLES_ROOT": str(default_samples_root),
    }
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    safe_log(
        logger,
        "info",
        "Runtime defaults recorder=%s transcriber=%s vad=%s",
        os.environ.get("STRUDEL_RECORDER_BACKEND"),
        os.environ.get("STRUDEL_TRANSCRIBER_BACKEND"),
        os.environ.get("STRUDEL_VAD_BACKEND"),
    )


def control_panel_script(default_session_id: str) -> str:
    return f"""
(() => {{
  if (window.__strudelVoicePanelReady) {{
    return "already-installed";
  }}
  window.__strudelVoicePanelReady = true;
  try {{
    delete window.strudelVoiceStart;
    delete window.strudelVoiceReload;
    delete window.strudelVoiceStop;
  }} catch (_err) {{
    // Ignore.
  }}

  const params = new URLSearchParams(window.location.search);
  const state = {{
    sessionId: params.get("svSession") || {default_session_id!r},
    baseUrl: (params.get("svBase") || window.location.origin).replace(/\\/$/, ""),
  }};

  const openButton = document.createElement("button");
  openButton.textContent = "Voice";
  openButton.setAttribute("type", "button");
  openButton.style.position = "fixed";
  openButton.style.right = "16px";
  openButton.style.bottom = "16px";
  openButton.style.zIndex = "99999";
  openButton.style.border = "0";
  openButton.style.borderRadius = "999px";
  openButton.style.padding = "10px 14px";
  openButton.style.background = "#111827";
  openButton.style.color = "#ffffff";
  openButton.style.cursor = "pointer";
  openButton.style.fontSize = "13px";
  openButton.style.boxShadow = "0 4px 14px rgba(0, 0, 0, 0.25)";

  const overlay = document.createElement("div");
  overlay.style.position = "fixed";
  overlay.style.inset = "0";
  overlay.style.display = "none";
  overlay.style.alignItems = "center";
  overlay.style.justifyContent = "center";
  overlay.style.zIndex = "100000";
  overlay.style.background = "rgba(17, 24, 39, 0.45)";

  const panel = document.createElement("div");
  panel.style.width = "340px";
  panel.style.maxWidth = "calc(100vw - 32px)";
  panel.style.background = "#ffffff";
  panel.style.borderRadius = "12px";
  panel.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.25)";
  panel.style.padding = "16px";
  panel.style.fontFamily = "system-ui, sans-serif";

  const title = document.createElement("div");
  title.textContent = "Control de muestreo de voz";
  title.style.fontSize = "16px";
  title.style.fontWeight = "700";
  title.style.marginBottom = "12px";

  const inputLabel = document.createElement("label");
  inputLabel.textContent = "ID de sesion";
  inputLabel.style.display = "block";
  inputLabel.style.fontSize = "12px";
  inputLabel.style.color = "#374151";
  inputLabel.style.marginBottom = "6px";

  const sessionInput = document.createElement("input");
  sessionInput.type = "text";
  sessionInput.value = state.sessionId;
  sessionInput.style.width = "100%";
  sessionInput.style.border = "1px solid #d1d5db";
  sessionInput.style.borderRadius = "8px";
  sessionInput.style.padding = "8px 10px";
  sessionInput.style.marginBottom = "12px";
  sessionInput.style.boxSizing = "border-box";

  const storageLabel = document.createElement("label");
  storageLabel.textContent = "Ubicacion de guardado";
  storageLabel.style.display = "block";
  storageLabel.style.fontSize = "12px";
  storageLabel.style.color = "#374151";
  storageLabel.style.marginBottom = "6px";

  const storageInfo = document.createElement("div");
  storageInfo.textContent = "Cargando rutas...";
  storageInfo.style.fontSize = "11px";
  storageInfo.style.lineHeight = "1.45";
  storageInfo.style.color = "#374151";
  storageInfo.style.background = "#f9fafb";
  storageInfo.style.border = "1px solid #e5e7eb";
  storageInfo.style.borderRadius = "8px";
  storageInfo.style.padding = "8px 10px";
  storageInfo.style.marginBottom = "12px";
  storageInfo.style.whiteSpace = "pre-wrap";
  storageInfo.style.wordBreak = "break-all";

  const openStorageButton = document.createElement("button");
  openStorageButton.textContent = "Abrir carpeta";
  openStorageButton.type = "button";
  openStorageButton.style.width = "100%";
  openStorageButton.style.padding = "8px";
  openStorageButton.style.marginBottom = "12px";
  openStorageButton.style.borderRadius = "8px";
  openStorageButton.style.border = "1px solid #6b7280";
  openStorageButton.style.background = "#ffffff";
  openStorageButton.style.color = "#111827";
  openStorageButton.style.cursor = "pointer";

  const actions = document.createElement("div");
  actions.style.display = "grid";
  actions.style.gridTemplateColumns = "1fr 1fr 1fr";
  actions.style.gap = "8px";

  const modeLabel = document.createElement("label");
  modeLabel.textContent = "Tipo de importacion";
  modeLabel.style.display = "block";
  modeLabel.style.fontSize = "12px";
  modeLabel.style.color = "#374151";
  modeLabel.style.marginBottom = "6px";
  modeLabel.style.marginTop = "2px";

  const modeSelect = document.createElement("select");
  modeSelect.style.width = "100%";
  modeSelect.style.border = "1px solid #d1d5db";
  modeSelect.style.borderRadius = "8px";
  modeSelect.style.padding = "8px 10px";
  modeSelect.style.marginBottom = "12px";
  modeSelect.style.boxSizing = "border-box";
  [
    ["sentences", "Oraciones"],
    ["phrases", "Frases"],
    ["words", "Palabras"],
    ["letters", "Letras"],
  ].forEach(([value, label]) => {{
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    modeSelect.appendChild(option);
  }});

  const startButton = document.createElement("button");
  startButton.textContent = "Iniciar";
  startButton.type = "button";
  startButton.style.padding = "8px";
  startButton.style.borderRadius = "8px";
  startButton.style.border = "1px solid #16a34a";
  startButton.style.background = "#16a34a";
  startButton.style.color = "#ffffff";
  startButton.style.cursor = "pointer";

  const stopButton = document.createElement("button");
  stopButton.textContent = "Detener";
  stopButton.type = "button";
  stopButton.style.padding = "8px";
  stopButton.style.borderRadius = "8px";
  stopButton.style.border = "1px solid #dc2626";
  stopButton.style.background = "#dc2626";
  stopButton.style.color = "#ffffff";
  stopButton.style.cursor = "pointer";

  const importButton = document.createElement("button");
  importButton.textContent = "Importar";
  importButton.type = "button";
  importButton.style.padding = "8px";
  importButton.style.borderRadius = "8px";
  importButton.style.border = "1px solid #2563eb";
  importButton.style.background = "#2563eb";
  importButton.style.color = "#ffffff";
  importButton.style.cursor = "pointer";

  const closeButton = document.createElement("button");
  closeButton.textContent = "Cerrar";
  closeButton.type = "button";
  closeButton.style.marginTop = "12px";
  closeButton.style.width = "100%";
  closeButton.style.padding = "8px";
  closeButton.style.borderRadius = "8px";
  closeButton.style.border = "1px solid #d1d5db";
  closeButton.style.background = "#f9fafb";
  closeButton.style.color = "#111827";
  closeButton.style.cursor = "pointer";

  const status = document.createElement("div");
  status.style.minHeight = "18px";
  status.style.marginTop = "10px";
  status.style.fontSize = "12px";
  status.style.color = "#374151";

  const normalizeSessionId = () => {{
    const candidate = sessionInput.value.trim();
    if (!candidate) {{
      throw new Error("El ID de sesion no puede estar vacio");
    }}
    state.sessionId = candidate;
    return candidate;
  }};

  const setBusy = (busy) => {{
    [startButton, stopButton, importButton, closeButton, sessionInput, modeSelect].forEach((element) => {{
      element.disabled = busy;
    }});
    openButton.disabled = busy;
    openButton.style.opacity = busy ? "0.7" : "1";
  }};

  const setStatus = (message, isError = false) => {{
    status.textContent = message;
    status.style.color = isError ? "#b91c1c" : "#374151";
  }};

  const updateStorageInfo = async () => {{
    const sessionId = sessionInput.value.trim();
    const query = sessionId ? `?session_id=${{encodeURIComponent(sessionId)}}` : "";
    try {{
      const response = await fetch(`${{state.baseUrl}}/storage${{query}}`);
      if (!response.ok) {{
        throw new Error(String(response.status));
      }}
      const info = await response.json();
      const lines = [];
      if (info.raw_dir) {{
        lines.push(`RAW: ${{info.raw_dir}}`);
      }}
      if (info.workspace_dir) {{
        lines.push(`Muestras: ${{info.workspace_dir}}`);
      }} else if (info.samples_root) {{
        lines.push(`Raiz: ${{info.samples_root}}`);
      }}
      storageInfo.textContent = lines.join("\\n") || "No hay rutas disponibles";
    }} catch (_error) {{
      storageInfo.textContent = "No se pudo cargar la ruta de guardado";
    }}
  }};

  const requestJson = async (path, body) => {{
    const response = await fetch(`${{state.baseUrl}}${{path}}`, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(body),
    }});
    if (!response.ok) {{
      throw new Error(`${{response.status}} ${{await response.text()}}`);
    }}
    return response.json();
  }};

  const insertTextInEditor = async (text) => {{
    const target = document.activeElement;
    if (target && (target.tagName === "TEXTAREA" || target.isContentEditable)) {{
      target.focus();
      if (typeof document.execCommand === "function") {{
        const inserted = document.execCommand("insertText", false, text);
        if (inserted) {{
          return true;
        }}
      }}
    }}
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      await navigator.clipboard.writeText(text);
      return false;
    }}
    throw new Error("No se puede insertar automaticamente; copia manualmente la instruccion de importacion");
  }};

  openStorageButton.addEventListener("click", async () => {{
    const sessionId = sessionInput.value.trim();
    const query = sessionId ? `?session_id=${{encodeURIComponent(sessionId)}}` : "";
    try {{
      setBusy(true);
      setStatus("Abriendo carpeta...");
      await requestJson(`/storage/open${{query}}`, {{}});
      setStatus("Carpeta abierta");
    }} catch (error) {{
      setStatus(`Error al abrir la carpeta: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  startButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Iniciando grabacion...");
      await requestJson("/start", {{ session_id: sessionId }});
      setStatus(`Grabacion iniciada: ${{sessionId}}`);
    }} catch (error) {{
      setStatus(`Error al iniciar: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  stopButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Deteniendo grabacion...");
      await requestJson("/stop", {{ session_id: sessionId }});
      setStatus(`Grabacion detenida: ${{sessionId}}`);
    }} catch (error) {{
      setStatus(`Error al detener: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  importButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Importando...");
      const scriptUrl = `${{state.baseUrl}}/strudel/${{encodeURIComponent(sessionId)}}`;
      const selectedMode = modeSelect.value;
      const snippet =
        `// Strudel Voice import\\n` +
        `const sv = await import("${{scriptUrl}}");\\n` +
        `const strudelVoiceMode = "${{selectedMode}}";\\n` +
        `const strudelVoiceSamples = sv.strudelVoiceSamples[strudelVoiceMode] || [];\\n`;
      const inserted = await insertTextInEditor(snippet);
      if (inserted) {{
        setStatus("La instruccion de importacion se escribio en el editor");
      }} else {{
        setStatus("La instruccion de importacion se copio al portapapeles; pegala en el editor");
      }}
    }} catch (error) {{
      setStatus(`Error al importar: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  openButton.addEventListener("click", () => {{
    overlay.style.display = "flex";
    setStatus("");
    updateStorageInfo();
    sessionInput.focus();
    sessionInput.select();
  }});

  sessionInput.addEventListener("input", () => {{
    updateStorageInfo();
  }});

  closeButton.addEventListener("click", () => {{
    overlay.style.display = "none";
  }});

  overlay.addEventListener("click", (event) => {{
    if (event.target === overlay) {{
      overlay.style.display = "none";
    }}
  }});

  actions.appendChild(startButton);
  actions.appendChild(stopButton);
  actions.appendChild(importButton);
  panel.appendChild(title);
  panel.appendChild(inputLabel);
  panel.appendChild(sessionInput);
  panel.appendChild(storageLabel);
  panel.appendChild(storageInfo);
  panel.appendChild(openStorageButton);
  panel.appendChild(modeLabel);
  panel.appendChild(modeSelect);
  panel.appendChild(actions);
  panel.appendChild(status);
  panel.appendChild(closeButton);
  overlay.appendChild(panel);
  document.body.appendChild(openButton);
  document.body.appendChild(overlay);
  updateStorageInfo();
  return "installed";
}})();
"""

def control_panel_script(default_session_id: str) -> str:
    return f"""
(() => {{
  if (window.__strudelVoicePanelReady) {{
    return "already-installed";
  }}
  window.__strudelVoicePanelReady = true;

  const params = new URLSearchParams(window.location.search);
  const state = {{
    sessionId: params.get("svSession") || {default_session_id!r},
    baseUrl: (params.get("svBase") || window.location.origin).replace(/\\/$/, ""),
  }};

  const openButton = document.createElement("button");
  openButton.textContent = "Voice";
  Object.assign(openButton.style, {{
    position: "fixed",
    right: "16px",
    bottom: "16px",
    zIndex: "99999",
    border: "0",
    borderRadius: "999px",
    padding: "10px 14px",
    background: "#111827",
    color: "#ffffff",
    cursor: "pointer",
    fontSize: "13px",
    boxShadow: "0 4px 14px rgba(0, 0, 0, 0.25)",
  }});

  const overlay = document.createElement("div");
  Object.assign(overlay.style, {{
    position: "fixed",
    inset: "0",
    display: "none",
    alignItems: "center",
    justifyContent: "center",
    zIndex: "100000",
    background: "rgba(17, 24, 39, 0.45)",
  }});

  const panel = document.createElement("div");
  Object.assign(panel.style, {{
    width: "340px",
    maxWidth: "calc(100vw - 32px)",
    background: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.25)",
    padding: "16px",
    fontFamily: "system-ui, sans-serif",
  }});

  const title = document.createElement("div");
  title.textContent = "Control de muestreo de voz";
  Object.assign(title.style, {{
    fontSize: "16px",
    fontWeight: "700",
    marginBottom: "12px",
  }});

  const inputLabel = document.createElement("label");
  inputLabel.textContent = "ID de sesion";
  Object.assign(inputLabel.style, {{
    display: "block",
    fontSize: "12px",
    color: "#374151",
    marginBottom: "6px",
  }});

  const sessionInput = document.createElement("input");
  sessionInput.type = "text";
  sessionInput.value = state.sessionId;
  Object.assign(sessionInput.style, {{
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: "8px",
    padding: "8px 10px",
    marginBottom: "12px",
    boxSizing: "border-box",
    backgroundColor: "#ffffff",
    color: "#111827",
    caretColor: "#2563eb",
    fontSize: "16px",
    lineHeight: "22px",
  }});

  const storageLabel = document.createElement("label");
  storageLabel.textContent = "Ubicacion de guardado";
  Object.assign(storageLabel.style, {{
    display: "block",
    fontSize: "12px",
    color: "#374151",
    marginBottom: "6px",
  }});

  const storageInfo = document.createElement("div");
  storageInfo.textContent = "Cargando rutas...";
  Object.assign(storageInfo.style, {{
    fontSize: "11px",
    lineHeight: "1.45",
    color: "#374151",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "8px 10px",
    marginBottom: "12px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
  }});

  const openStorageButton = document.createElement("button");
  openStorageButton.textContent = "Abrir carpeta";
  openStorageButton.type = "button";
  Object.assign(openStorageButton.style, {{
    width: "100%",
    padding: "8px",
    marginBottom: "12px",
    borderRadius: "8px",
    border: "1px solid #6b7280",
    background: "#ffffff",
    color: "#111827",
    cursor: "pointer",
  }});

  const modeLabel = document.createElement("label");
  modeLabel.textContent = "Tipo de importacion";
  Object.assign(modeLabel.style, {{
    display: "block",
    fontSize: "12px",
    color: "#374151",
    marginBottom: "6px",
  }});

  const modeSelect = document.createElement("select");
  Object.assign(modeSelect.style, {{
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: "8px",
    padding: "8px 10px",
    marginBottom: "12px",
    boxSizing: "border-box",
    backgroundColor: "#ffffff",
    color: "#111827",
    fontSize: "16px",
    lineHeight: "22px",
  }});
  [
    ["sentences", "Oraciones"],
    ["phrases", "Frases"],
    ["words", "Palabras"],
    ["letters", "Letras"],
  ].forEach(([value, label]) => {{
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.style.color = "#111827";
    option.style.backgroundColor = "#ffffff";
    modeSelect.appendChild(option);
  }});

  const actions = document.createElement("div");
  Object.assign(actions.style, {{
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "8px",
  }});

  const makeActionButton = (text, background, border) => {{
    const button = document.createElement("button");
    button.textContent = text;
    button.type = "button";
    Object.assign(button.style, {{
      padding: "8px",
      borderRadius: "8px",
      border: `1px solid ${{border}}`,
      background,
      color: "#ffffff",
      cursor: "pointer",
    }});
    return button;
  }};

  const startButton = makeActionButton("Iniciar", "#16a34a", "#16a34a");
  const stopButton = makeActionButton("Detener", "#dc2626", "#dc2626");
  const importButton = makeActionButton("Importar", "#2563eb", "#2563eb");

  const closeButton = document.createElement("button");
  closeButton.textContent = "Cerrar";
  closeButton.type = "button";
  Object.assign(closeButton.style, {{
    marginTop: "12px",
    width: "100%",
    padding: "8px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    background: "#f9fafb",
    color: "#111827",
    cursor: "pointer",
  }});

  const status = document.createElement("div");
  Object.assign(status.style, {{
    minHeight: "18px",
    marginTop: "10px",
    fontSize: "12px",
    color: "#374151",
  }});

  const normalizeSessionId = () => {{
    const candidate = sessionInput.value.trim();
    if (!candidate) {{
      throw new Error("El ID de sesion no puede estar vacio");
    }}
    state.sessionId = candidate;
    return candidate;
  }};

  const setBusy = (busy) => {{
    [startButton, stopButton, importButton, closeButton, sessionInput, modeSelect].forEach((element) => {{
      element.disabled = busy;
    }});
    openButton.disabled = busy;
    openButton.style.opacity = busy ? "0.7" : "1";
  }};

  const setStatus = (message, isError = false) => {{
    status.textContent = message;
    status.style.color = isError ? "#b91c1c" : "#374151";
  }};

  const updateStorageInfo = async () => {{
    const sessionId = sessionInput.value.trim();
    const query = sessionId ? `?session_id=${{encodeURIComponent(sessionId)}}` : "";
    try {{
      const response = await fetch(`${{state.baseUrl}}/storage${{query}}`);
      if (!response.ok) {{
        throw new Error(String(response.status));
      }}
      const info = await response.json();
      const lines = [];
      if (info.raw_dir) {{
        lines.push(`RAW: ${{info.raw_dir}}`);
      }}
      if (info.workspace_dir) {{
        lines.push(`Muestras: ${{info.workspace_dir}}`);
      }} else if (info.samples_root) {{
        lines.push(`Raiz: ${{info.samples_root}}`);
      }}
      storageInfo.textContent = lines.join("\\n") || "No hay rutas disponibles";
    }} catch (_error) {{
      storageInfo.textContent = "No se pudo cargar la ruta de guardado";
    }}
  }};

  const requestJson = async (path, body) => {{
    const response = await fetch(`${{state.baseUrl}}${{path}}`, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(body),
    }});
    if (!response.ok) {{
      throw new Error(`${{response.status}} ${{await response.text()}}`);
    }}
    return response.json();
  }};

  const waitForVoiceImporter = async () => {{
    const started = Date.now();
    while (Date.now() - started < 10000) {{
      if (typeof window.strudelVoiceImportSamples === "function") {{
        return window.strudelVoiceImportSamples;
      }}
      await new Promise((resolve) => setTimeout(resolve, 100));
    }}
    throw new Error("La interfaz de importacion de Strudel aun no esta lista; intenta de nuevo en un momento");
  }};

  openStorageButton.addEventListener("click", async () => {{
    const sessionId = sessionInput.value.trim();
    const query = sessionId ? `?session_id=${{encodeURIComponent(sessionId)}}` : "";
    try {{
      setBusy(true);
      setStatus("Abriendo carpeta...");
      await requestJson(`/storage/open${{query}}`, {{}});
      setStatus("Carpeta abierta");
    }} catch (error) {{
      setStatus(`Error al abrir la carpeta: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  startButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Iniciando grabacion...");
      await requestJson("/start", {{ session_id: sessionId }});
      setStatus(`Grabacion iniciada: ${{sessionId}}`);
    }} catch (error) {{
      setStatus(`Error al iniciar: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  stopButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Deteniendo la grabacion y generando muestras...");
      await requestJson("/stop", {{ session_id: sessionId }});
      setStatus(`Grabacion detenida: ${{sessionId}}`);
    }} catch (error) {{
      setStatus(`Error al detener: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  importButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      setStatus("Importando a sounds/user...");
      const selectedMode = modeSelect.value;
      const importer = await waitForVoiceImporter();
      const result = await importer(sessionId, selectedMode);
      const label = modeSelect.options[modeSelect.selectedIndex].text;
      setStatus(`Se importaron ${{result.count}} muestras de ${{label}} a user`);
    }} catch (error) {{
      setStatus(`Error al importar: ${{String(error)}}`, true);
    }} finally {{
      setBusy(false);
    }}
  }});

  openButton.addEventListener("click", () => {{
    overlay.style.display = "flex";
    setStatus("");
    updateStorageInfo();
    sessionInput.focus();
    sessionInput.select();
  }});

  sessionInput.addEventListener("input", () => {{
    updateStorageInfo();
  }});

  closeButton.addEventListener("click", () => {{
    overlay.style.display = "none";
  }});

  overlay.addEventListener("click", (event) => {{
    if (event.target === overlay) {{
      overlay.style.display = "none";
    }}
  }});

  actions.appendChild(startButton);
  actions.appendChild(stopButton);
  actions.appendChild(importButton);
  panel.appendChild(title);
  panel.appendChild(inputLabel);
  panel.appendChild(sessionInput);
  panel.appendChild(storageLabel);
  panel.appendChild(storageInfo);
  panel.appendChild(openStorageButton);
  panel.appendChild(modeLabel);
  panel.appendChild(modeSelect);
  panel.appendChild(actions);
  panel.appendChild(status);
  panel.appendChild(closeButton);
  overlay.appendChild(panel);
  document.body.appendChild(openButton);
  document.body.appendChild(overlay);
  updateStorageInfo();
  return "installed";
}})();
"""


def main() -> None:
    logger, _ = setup_logging()
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    base_url = f"http://{host}:{port}"
    runtime_root = resolve_runtime_root()
    configure_ffmpeg_environment(runtime_root, logger)
    configure_runtime_defaults(logger)

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
                        safe_log(logger, "info", "Voice control panel injected.")
                        return
                except Exception:
                    # Window may not be ready yet.
                    pass
                time.sleep(0.25)
            safe_log(logger, "warning", "Voice control panel injection timed out.")

        webview.start(inject_control_panel, window)
    finally:
        safe_log(logger, "info", "Launcher exited.")


if __name__ == "__main__":
    main()
