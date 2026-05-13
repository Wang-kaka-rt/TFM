from __future__ import annotations


def control_panel_script(default_session_id: str) -> str:
    """Return the self-installing voice control panel as an IIFE JavaScript string.

    The script is idempotent (guarded by ``window.__strudelVoicePanelReady``) so
    it is safe to inject both via HTML and via pywebview's ``evaluate_js``.
    """
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
    busy: false,
    isRecording: false,
    isUploading: false,
    isProcessing: false,
    runtimeDiagnostics: null,
    visualizer: null,
    browserRecorder: null,
    browserUploadChain: Promise.resolve(),
    recordingStartedAt: 0,
    recordingTimerId: 0,
    previewPollId: 0,
    stopPollId: 0,
    previewWords: [],
  }};

  const styleTag = document.createElement("style");
  styleTag.textContent = `
    @keyframes strudelVoicePanelPulse {{
      0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.35); }}
      70% {{ transform: scale(1.08); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }}
      100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
    }}
    @keyframes strudelVoicePanelSpin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .strudel-voice-scroll {{
      scrollbar-width: thin;
      scrollbar-color: rgba(148, 163, 184, 0.75) transparent;
    }}
    .strudel-voice-scroll::-webkit-scrollbar {{
      width: 8px;
    }}
    .strudel-voice-scroll::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .strudel-voice-scroll::-webkit-scrollbar-thumb {{
      background: linear-gradient(180deg, rgba(191, 219, 254, 0.95), rgba(148, 163, 184, 0.9));
      border-radius: 999px;
      border: 2px solid transparent;
      background-clip: padding-box;
    }}
    .strudel-voice-scroll::-webkit-scrollbar-thumb:hover {{
      background: linear-gradient(180deg, rgba(96, 165, 250, 0.95), rgba(100, 116, 139, 0.95));
      border-radius: 999px;
      border: 2px solid transparent;
      background-clip: padding-box;
    }}
  `;
  document.head.appendChild(styleTag);

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
    fontWeight: "700",
    transition: "background 120ms ease, box-shadow 120ms ease, opacity 120ms ease",
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
    width: "720px",
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
    marginBottom: "10px",
  }});

  const contentLayout = document.createElement("div");
  Object.assign(contentLayout.style, {{
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.05fr) minmax(0, 0.95fr)",
    gap: "14px",
    alignItems: "start",
  }});

  const leftColumn = document.createElement("div");
  Object.assign(leftColumn.style, {{
    minWidth: "0",
  }});

  const rightColumn = document.createElement("div");
  Object.assign(rightColumn.style, {{
    minWidth: "0",
  }});

  const recordingState = document.createElement("div");
  Object.assign(recordingState.style, {{
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: "10px 12px",
    padding: "10px 12px",
    marginBottom: "12px",
    borderRadius: "10px",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
  }});

  const recordingPrimary = document.createElement("div");
  Object.assign(recordingPrimary.style, {{
    display: "flex",
    alignItems: "center",
    gap: "10px",
    minWidth: "0",
  }});

  const recordingDot = document.createElement("div");
  Object.assign(recordingDot.style, {{
    width: "10px",
    height: "10px",
    borderRadius: "999px",
    background: "#9ca3af",
    flexShrink: "0",
    transition: "background 120ms ease, box-shadow 120ms ease",
  }});

  const recordingCopy = document.createElement("div");
  Object.assign(recordingCopy.style, {{
    minWidth: "0",
  }});

  const recordingText = document.createElement("div");
  recordingText.textContent = "Listo para grabar";
  Object.assign(recordingText.style, {{
    fontSize: "13px",
    fontWeight: "600",
    color: "#374151",
  }});

  const recordingHint = document.createElement("div");
  recordingHint.textContent = "El microfono espera la orden de inicio";
  Object.assign(recordingHint.style, {{
    marginTop: "2px",
    fontSize: "11px",
    color: "#6b7280",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  }});

  const recordingTimer = document.createElement("div");
  recordingTimer.textContent = "00:00";
  Object.assign(recordingTimer.style, {{
    alignSelf: "start",
    padding: "4px 8px",
    borderRadius: "999px",
    background: "#e5e7eb",
    color: "#374151",
    fontSize: "12px",
    fontWeight: "700",
    fontVariantNumeric: "tabular-nums",
  }});

  const levelMeterWrap = document.createElement("div");
  Object.assign(levelMeterWrap.style, {{
    gridColumn: "1 / span 2",
    display: "grid",
    gridTemplateColumns: "1fr auto",
    alignItems: "center",
    gap: "8px",
  }});

  const levelMeterTrack = document.createElement("div");
  Object.assign(levelMeterTrack.style, {{
    height: "8px",
    borderRadius: "999px",
    background: "#e5e7eb",
    overflow: "hidden",
  }});

  const levelMeterFill = document.createElement("div");
  Object.assign(levelMeterFill.style, {{
    width: "0%",
    height: "100%",
    borderRadius: "999px",
    background: "linear-gradient(90deg, #22c55e 0%, #f59e0b 60%, #ef4444 100%)",
    transition: "width 80ms linear",
  }});
  levelMeterTrack.appendChild(levelMeterFill);

  const levelMeterText = document.createElement("div");
  levelMeterText.textContent = "Nivel 0%";
  Object.assign(levelMeterText.style, {{
    width: "62px",
    textAlign: "right",
    fontSize: "11px",
    fontWeight: "600",
    color: "#6b7280",
    fontVariantNumeric: "tabular-nums",
  }});

  recordingCopy.appendChild(recordingText);
  recordingCopy.appendChild(recordingHint);
  recordingPrimary.appendChild(recordingDot);
  recordingPrimary.appendChild(recordingCopy);
  levelMeterWrap.appendChild(levelMeterTrack);
  levelMeterWrap.appendChild(levelMeterText);
  recordingState.appendChild(recordingPrimary);
  recordingState.appendChild(recordingTimer);
  recordingState.appendChild(levelMeterWrap);

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

  const runtimeLabel = document.createElement("label");
  runtimeLabel.textContent = "Estado de audio";
  Object.assign(runtimeLabel.style, {{
    display: "block",
    fontSize: "12px",
    color: "#374151",
    marginBottom: "6px",
  }});

  const runtimeInfo = document.createElement("div");
  runtimeInfo.textContent = "Comprobando audio...";
  Object.assign(runtimeInfo.style, {{
    fontSize: "11px",
    lineHeight: "1.5",
    color: "#374151",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "8px 10px",
    marginBottom: "12px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  }});

  const processingCard = document.createElement("div");
  Object.assign(processingCard.style, {{
    minHeight: "238px",
    marginTop: "12px",
    padding: "12px",
    borderRadius: "12px",
    border: "1px solid #e5e7eb",
    background: "#f9fafb",
    display: "flex",
    flexDirection: "column",
    alignItems: "stretch",
    justifyContent: "flex-start",
    textAlign: "center",
    boxSizing: "border-box",
  }});

  const processingSpinner = document.createElement("div");
  Object.assign(processingSpinner.style, {{
    width: "42px",
    height: "42px",
    marginBottom: "14px",
    borderRadius: "999px",
    border: "4px solid #dbeafe",
    borderTopColor: "#2563eb",
    animation: "strudelVoicePanelSpin 0.9s linear infinite",
    display: "none",
  }});

  const processingTitle = document.createElement("div");
  processingTitle.textContent = "Palabras detectadas";
  Object.assign(processingTitle.style, {{
    fontSize: "15px",
    fontWeight: "700",
    color: "#374151",
    marginTop: "2px",
  }});

  const processingHint = document.createElement("div");
  processingHint.textContent = "Mientras grabas, aqui apareceran las palabras que ya se hayan convertido.";
  Object.assign(processingHint.style, {{
    marginTop: "8px",
    fontSize: "12px",
    lineHeight: "1.5",
    color: "#6b7280",
    maxWidth: "260px",
  }});

  const processingWords = document.createElement("div");
  processingWords.className = "strudel-voice-scroll";
  Object.assign(processingWords.style, {{
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gridAutoRows: "36px",
    gap: "6px",
    width: "100%",
    marginTop: "8px",
    flex: "1 1 auto",
    minHeight: "0",
    alignItems: "stretch",
    alignContent: "start",
    maxHeight: "204px",
    overflowY: "auto",
    overflowX: "hidden",
    paddingRight: "2px",
    boxSizing: "border-box",
    scrollbarGutter: "stable",
  }});

  const renderPreviewWords = () => {{
    processingWords.replaceChildren();
    const hasWords = state.previewWords.length > 0;

    processingTitle.style.display = hasWords ? "none" : "block";
    processingHint.style.display = hasWords ? "none" : "block";
    processingWords.style.marginTop = hasWords ? "0" : "8px";

    if (!hasWords) {{
      const emptyState = document.createElement("div");
      emptyState.textContent = state.isRecording
        ? "Aun no hay palabras listas en este bloque."
        : state.isUploading
          ? "Subiendo el ultimo bloque de audio. Espera un momento."
        : state.isProcessing
          ? "Procesando en segundo plano. Las palabras apareceran en cuanto terminen de convertirse."
        : "Todavia no hay palabras convertidas.";
      Object.assign(emptyState.style, {{
        gridColumn: "1 / -1",
        fontSize: "12px",
        color: "#6b7280",
        textAlign: "center",
      }});
      processingWords.appendChild(emptyState);
      return;
    }}

    state.previewWords.forEach((item) => {{
      const chip = document.createElement("div");
      chip.textContent = `${{item.text}}(${{item.count}})`;
      Object.assign(chip.style, {{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "36px",
        width: "100%",
        boxSizing: "border-box",
        padding: "0 6px",
        borderRadius: "12px",
        border: "1px solid #d1d5db",
        background: "#ffffff",
        color: "#2563eb",
        fontSize: "12px",
        fontWeight: "700",
        textAlign: "center",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }});
      processingWords.appendChild(chip);
    }});
  }};

  processingCard.appendChild(processingSpinner);
  processingCard.appendChild(processingTitle);
  processingCard.appendChild(processingHint);
  processingCard.appendChild(processingWords);

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

  const stackSection = (elements) => {{
    const wrapper = document.createElement("div");
    Object.assign(wrapper.style, {{
      display: "flex",
      flexDirection: "column",
    }});
    elements.forEach((element) => {{
      wrapper.appendChild(element);
    }});
    return wrapper;
  }};

  const status = document.createElement("div");
  Object.assign(status.style, {{
    minHeight: "18px",
    marginTop: "10px",
    fontSize: "12px",
    color: "#374151",
  }});

  const visualizerCard = document.createElement("div");
  Object.assign(visualizerCard.style, {{
    marginTop: "12px",
    padding: "10px 12px 12px",
    borderRadius: "10px",
    border: "1px solid #e5e7eb",
    background: "#0f172a",
    opacity: "0.65",
    transition: "opacity 120ms ease",
  }});

  const visualizerLabel = document.createElement("div");
  visualizerLabel.textContent = "Senal del microfono";
  Object.assign(visualizerLabel.style, {{
    marginBottom: "8px",
    fontSize: "11px",
    fontWeight: "600",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    color: "#cbd5e1",
  }});

  const visualizerCanvas = document.createElement("canvas");
  visualizerCanvas.width = 308;
  visualizerCanvas.height = 76;
  Object.assign(visualizerCanvas.style, {{
    width: "100%",
    height: "76px",
    display: "block",
    borderRadius: "8px",
    background: "#020617",
  }});

  visualizerCard.appendChild(visualizerLabel);
  visualizerCard.appendChild(visualizerCanvas);

  const normalizeSessionId = () => {{
    const candidate = sessionInput.value.trim();
    if (!candidate) {{
      throw new Error("El ID de sesion no puede estar vacio");
    }}
    state.sessionId = candidate;
    return candidate;
  }};

  const setStatus = (message, isError = false) => {{
    status.textContent = message;
    status.style.color = isError ? "#b91c1c" : "#374151";
  }};

  const formatRuntimeErrorMessage = async (response) => {{
    const text = await response.text();
    if (!text.trim()) {{
      return `HTTP ${{response.status}}`;
    }}
    try {{
      const payload = JSON.parse(text);
      if (typeof payload?.detail === "string" && payload.detail.trim()) {{
        return payload.detail.trim();
      }}
      if (typeof payload?.message === "string" && payload.message.trim()) {{
        return payload.message.trim();
      }}
      return JSON.stringify(payload);
    }} catch (_error) {{
      return text.trim() || `HTTP ${{response.status}}`;
    }}
  }};

  const renderRuntimeInfo = (payload) => {{
    if (!payload) {{
      runtimeInfo.textContent = "No hay diagnostico disponible";
      runtimeInfo.style.color = "#374151";
      runtimeInfo.style.background = "#f9fafb";
      runtimeInfo.style.borderColor = "#e5e7eb";
      return;
    }}

    const recorder = payload.recorder || {{}};
    const transcriber = payload.transcriber || {{}};
    const audio = payload.audio || null;
    const lines = [];
    const recorderReady = !!recorder.ready;
    const transcriberReady = !!transcriber.ready;

    lines.push(
      `Grabacion: ${{recorderReady ? "lista" : "no disponible"}} ` +
      `(${{recorder.configured_backend || "desconocido"}} -> ${{recorder.effective_backend || "desconocido"}})`,
    );
    if (recorder.effective_backend === "browser") {{
      lines.push("Captura de microfono: navegador/webview");
    }}
    if (audio) {{
      const selectedDevice = audio.selected_input_device?.name || "sin dispositivo";
      const defaultDevice = audio.default_input_device?.name || "sin predeterminado";
      const selectedSource = audio.selected_input_device_source || "unknown";
      lines.push(`Entradas detectadas: ${{audio.input_device_count ?? 0}}`);
      lines.push(`Microfono seleccionado: ${{selectedDevice}}`);
      lines.push(`Origen de seleccion: ${{selectedSource}}`);
      lines.push(`Microfono predeterminado: ${{defaultDevice}}`);
    }}
    if (recorder.init_error) {{
      lines.push(`Error de grabacion: ${{recorder.init_error}}`);
    }}
    lines.push(
      `Reconocimiento: ${{transcriberReady ? "listo" : "no disponible"}} ` +
      `(${{transcriber.configured_backend || "desconocido"}} -> ${{transcriber.effective_backend || "desconocido"}})`,
    );
    if (transcriber.init_error) {{
      lines.push(`Error de reconocimiento: ${{transcriber.init_error}}`);
    }}

    runtimeInfo.textContent = lines.join("\\n");
    const hasError = !recorderReady || !transcriberReady;
    runtimeInfo.style.color = hasError ? "#991b1b" : "#166534";
    runtimeInfo.style.background = hasError ? "#fef2f2" : "#f0fdf4";
    runtimeInfo.style.borderColor = hasError ? "#fecaca" : "#bbf7d0";
  }};

  const updateRuntimeInfo = async () => {{
    try {{
      const response = await fetch(`${{state.baseUrl}}/runtime`);
      if (!response.ok) {{
        throw new Error(await formatRuntimeErrorMessage(response));
      }}
      state.runtimeDiagnostics = await response.json();
      const sessionId = normalizeSessionId();
      if (sessionId) {{
        try {{
          const session = await fetchSessionStatus(sessionId);
          if (session?.state === "processing") {{
            state.isRecording = false;
            if (!state.isUploading) {{
              state.isProcessing = true;
            }}
            if (!state.stopPollId) {{
              startStopPolling(sessionId);
            }}
          }} else if (session?.state === "stopped" || session?.state === "failed") {{
            state.isUploading = false;
            state.isProcessing = false;
            stopStopPolling();
          }}
          refreshControls();
        }} catch (_statusError) {{
          // Runtime diagnostics should still render even if session status lookup fails.
        }}
      }}
      renderRuntimeInfo(state.runtimeDiagnostics);
      return state.runtimeDiagnostics;
    }} catch (error) {{
      state.runtimeDiagnostics = null;
      runtimeInfo.textContent = `No se pudo cargar el diagnostico: ${{String(error)}}`;
      runtimeInfo.style.color = "#991b1b";
      runtimeInfo.style.background = "#fef2f2";
      runtimeInfo.style.borderColor = "#fecaca";
      return null;
    }}
  }};

  const formatElapsed = (elapsedMs) => {{
    const totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${{minutes}}:${{seconds}}`;
  }};

  const updateRecordingClock = () => {{
    if (!state.isRecording || !state.recordingStartedAt) {{
      recordingTimer.textContent = "00:00";
      return;
    }}
    recordingTimer.textContent = formatElapsed(Date.now() - state.recordingStartedAt);
  }};

  const startRecordingClock = () => {{
    state.recordingStartedAt = Date.now();
    updateRecordingClock();
    if (state.recordingTimerId) {{
      window.clearInterval(state.recordingTimerId);
    }}
    state.recordingTimerId = window.setInterval(updateRecordingClock, 250);
  }};

  const stopRecordingClock = () => {{
    if (state.recordingTimerId) {{
      window.clearInterval(state.recordingTimerId);
      state.recordingTimerId = 0;
    }}
    state.recordingStartedAt = 0;
    updateRecordingClock();
  }};

  const setLevelMeter = (level) => {{
    const safeLevel = Math.max(0, Math.min(1, level));
    levelMeterFill.style.width = `${{Math.round(safeLevel * 100)}}%`;
    levelMeterText.textContent = `Nivel ${{String(Math.round(safeLevel * 100)).padStart(2, "0")}}%`;
  }};

  const stopPreviewPolling = () => {{
    if (state.previewPollId) {{
      window.clearInterval(state.previewPollId);
      state.previewPollId = 0;
    }}
  }};

  const stopStopPolling = () => {{
    if (state.stopPollId) {{
      window.clearInterval(state.stopPollId);
      state.stopPollId = 0;
    }}
  }};

  const concatenateFloat32Buffers = (buffers) => {{
    let totalLength = 0;
    buffers.forEach((buffer) => {{
      totalLength += buffer.length;
    }});
    const merged = new Float32Array(totalLength);
    let offset = 0;
    buffers.forEach((buffer) => {{
      merged.set(buffer, offset);
      offset += buffer.length;
    }});
    return merged;
  }};

  const encodeWavBlob = (buffers, sampleRate) => {{
    const samples = concatenateFloat32Buffers(buffers);
    const bytesPerSample = 2;
    const blockAlign = bytesPerSample;
    const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
    const view = new DataView(buffer);
    const writeString = (offset, value) => {{
      for (let index = 0; index < value.length; index += 1) {{
        view.setUint8(offset + index, value.charCodeAt(index));
      }}
    }};

    writeString(0, "RIFF");
    view.setUint32(4, 36 + samples.length * bytesPerSample, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, samples.length * bytesPerSample, true);

    let offset = 44;
    for (let index = 0; index < samples.length; index += 1) {{
      const clamped = Math.max(-1, Math.min(1, samples[index]));
      const pcm = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
      view.setInt16(offset, pcm, true);
      offset += bytesPerSample;
    }}

    return new Blob([buffer], {{ type: "audio/wav" }});
  }};

  const uploadBrowserChunk = async (blob) => {{
    const sessionId = normalizeSessionId();
    const response = await fetch(
      `${{state.baseUrl}}/browser/chunk?session_id=${{encodeURIComponent(sessionId)}}`,
      {{
        method: "POST",
        headers: {{ "Content-Type": "audio/wav" }},
        body: blob,
      }},
    );
    if (!response.ok) {{
      throw new Error(await formatRuntimeErrorMessage(response));
    }}
    await response.json();
    await refreshWordPreview();
  }};

  const flushBrowserChunk = async () => {{
    const recorder = state.browserRecorder;
    if (!recorder) {{
      return;
    }}
    if (!recorder.buffers.length) {{
      return;
    }}

    const buffers = recorder.buffers;
    recorder.buffers = [];
    const blob = encodeWavBlob(buffers, recorder.sampleRate);
    const uploadChain = state.browserUploadChain
      .catch(() => undefined)
      .then(() => uploadBrowserChunk(blob));
    state.browserUploadChain = uploadChain;
    await uploadChain;
  }};

  const queueBrowserChunkUpload = (buffers, sampleRate) => {{
    if (!buffers.length) {{
      return state.browserUploadChain;
    }}
    const blob = encodeWavBlob(buffers, sampleRate);
    const uploadChain = state.browserUploadChain
      .catch(() => undefined)
      .then(() => uploadBrowserChunk(blob));
    state.browserUploadChain = uploadChain;
    return uploadChain;
  }};

  const refreshWordPreview = async () => {{
    const sessionId = sessionInput.value.trim();
    if (!sessionId) {{
      state.previewWords = [];
      renderPreviewWords();
      return;
    }}

    try {{
      const response = await fetch(
        `${{state.baseUrl}}/samples/${{encodeURIComponent(sessionId)}}/manifest?t=${{Date.now()}}`,
      );
      if (!response.ok) {{
        if (response.status === 404) {{
          state.previewWords = [];
          renderPreviewWords();
          return;
        }}
        throw new Error(String(response.status));
      }}

      const manifest = await response.json();
      const words = Array.isArray(manifest?.words) ? manifest.words : [];
      const counts = new Map();
      words.forEach((item) => {{
        const label = String(item.text || item.name || "").trim().toLowerCase();
        if (!label) {{
          return;
        }}
        counts.set(label, (counts.get(label) || 0) + 1);
      }});

      state.previewWords = Array.from(counts.entries())
        .sort((a, b) => {{
          if (b[1] !== a[1]) {{
            return b[1] - a[1];
          }}
          return a[0].localeCompare(b[0], undefined, {{ sensitivity: "base" }});
        }})
        .map(([text, count]) => ({{ text, count }}));
      renderPreviewWords();
    }} catch (_error) {{
      if (!state.isRecording && !state.isProcessing) {{
        state.previewWords = [];
      }}
      renderPreviewWords();
    }}
  }};

  const fetchSessionStatus = async (sessionId) => {{
    const response = await fetch(
      `${{state.baseUrl}}/status?session_id=${{encodeURIComponent(sessionId)}}&t=${{Date.now()}}`,
    );
    if (!response.ok) {{
      throw new Error(await formatRuntimeErrorMessage(response));
    }}
    const payload = await response.json();
    return payload?.sessions?.[0] || null;
  }};

  const startStopPolling = (sessionId) => {{
    stopStopPolling();
    state.stopPollId = window.setInterval(async () => {{
      try {{
        const session = await fetchSessionStatus(sessionId);
        if (!session) {{
          return;
        }}
        if (session.state === "stopped") {{
          state.isProcessing = false;
          stopStopPolling();
          stopPreviewPolling();
          await refreshWordPreview();
          refreshControls();
          setStatus(`Grabacion procesada: ${{sessionId}}. Ya puedes importar las muestras.`);
          return;
        }}
        if (session.state === "failed") {{
          state.isProcessing = false;
          stopStopPolling();
          stopPreviewPolling();
          refreshControls();
          setStatus(`Error al procesar en segundo plano: ${{session.last_error || "desconocido"}}`, true);
        }}
      }} catch (_error) {{
        // Keep polling in background; transient errors should not block the UI.
      }}
    }}, 900);
  }};

  const startPreviewPolling = () => {{
    stopPreviewPolling();
    void refreshWordPreview();
    state.previewPollId = window.setInterval(() => {{
      void refreshWordPreview();
    }}, 900);
  }};

  const paintVisualizerIdle = () => {{
    const context = visualizerCanvas.getContext("2d");
    if (!context) {{
      return;
    }}

    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#020617";
    context.fillRect(0, 0, width, height);
    context.strokeStyle = "rgba(148, 163, 184, 0.35)";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(0, height / 2);
    context.lineTo(width, height / 2);
    context.stroke();
  }};

  const drawVisualizerFrame = (analyser, samples) => {{
    const context = visualizerCanvas.getContext("2d");
    if (!context) {{
      return;
    }}

    analyser.getByteTimeDomainData(samples);
    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#020617";
    context.fillRect(0, 0, width, height);

    let totalDeviation = 0;
    for (let i = 0; i < samples.length; i += 1) {{
      totalDeviation += Math.abs(samples[i] - 128);
    }}
    const amplitude = totalDeviation / samples.length;
    const level = Math.min(1, amplitude / 36);
    setLevelMeter(level);

    context.fillStyle = "rgba(239, 68, 68, 0.18)";
    context.fillRect(0, height - 6, width * level, 6);

    context.strokeStyle = "rgba(239, 68, 68, 0.95)";
    context.lineWidth = 2;
    context.beginPath();
    const sliceWidth = width / samples.length;
    let x = 0;
    for (let i = 0; i < samples.length; i += 1) {{
      const value = samples[i] / 128.0;
      const y = (value * height) / 2;
      if (i === 0) {{
        context.moveTo(x, y);
      }} else {{
        context.lineTo(x, y);
      }}
      x += sliceWidth;
    }}
    context.stroke();
  }};

  const stopVisualizer = async () => {{
    const activeVisualizer = state.visualizer;
    state.visualizer = null;

    if (!activeVisualizer) {{
      paintVisualizerIdle();
      setLevelMeter(0);
      return;
    }}

    if (activeVisualizer.animationFrame) {{
      cancelAnimationFrame(activeVisualizer.animationFrame);
    }}

    try {{
      activeVisualizer.source.disconnect();
    }} catch (_error) {{
      // Ignore disconnect failures during cleanup.
    }}

    if (activeVisualizer.captureProcessor) {{
      try {{
        activeVisualizer.captureProcessor.disconnect();
      }} catch (_error) {{
        // Ignore disconnect failures during cleanup.
      }}
    }}

    if (activeVisualizer.captureGain) {{
      try {{
        activeVisualizer.captureGain.disconnect();
      }} catch (_error) {{
        // Ignore disconnect failures during cleanup.
      }}
    }}

    activeVisualizer.stream.getTracks().forEach((track) => track.stop());

    if (activeVisualizer.audioContext && activeVisualizer.audioContext.state !== "closed") {{
      try {{
        await activeVisualizer.audioContext.close();
      }} catch (_error) {{
        // Ignore close failures during cleanup.
      }}
    }}

    paintVisualizerIdle();
    setLevelMeter(0);
  }};

  const startVisualizer = async () => {{
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
      throw new Error("Esta ventana no permite mostrar la senal del microfono.");
    }}

    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) {{
      throw new Error("AudioContext no esta disponible en esta ventana.");
    }}

    await stopVisualizer();

    const stream = await navigator.mediaDevices.getUserMedia({{
      audio: {{
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }},
    }});

    const audioContext = new AudioContextCtor();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.85;
    source.connect(analyser);

    const samples = new Uint8Array(analyser.fftSize);
    state.visualizer = {{
      audioContext,
      stream,
      source,
      analyser,
      animationFrame: 0,
    }};

    if (audioContext.state === "suspended") {{
      await audioContext.resume().catch(() => undefined);
    }}

    const render = () => {{
      if (!state.visualizer || state.visualizer.analyser !== analyser) {{
        return;
      }}
      drawVisualizerFrame(analyser, samples);
      state.visualizer.animationFrame = requestAnimationFrame(render);
    }};

    render();
  }};

  const startBrowserRecorder = async () => {{
    if (!state.visualizer) {{
      throw new Error("La captura del navegador necesita una senal de microfono activa.");
    }}
    await stopBrowserRecorder({{ flushFinal: false }});
    const chunkDurationSeconds = Number(state.runtimeDiagnostics?.recorder?.chunk_duration_seconds || 2.5);
    const audioContext = state.visualizer.audioContext;
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    const captureGain = audioContext.createGain();
    captureGain.gain.value = 0;

    processor.onaudioprocess = (event) => {{
      if (!state.isRecording || !state.browserRecorder) {{
        return;
      }}
      const input = event.inputBuffer.getChannelData(0);
      state.browserRecorder.buffers.push(new Float32Array(input));
    }};

    state.visualizer.source.connect(processor);
    processor.connect(captureGain);
    captureGain.connect(audioContext.destination);
    state.visualizer.captureProcessor = processor;
    state.visualizer.captureGain = captureGain;
    state.browserUploadChain = Promise.resolve();
    state.browserRecorder = {{
      processor,
      captureGain,
      sampleRate: audioContext.sampleRate || 48000,
      buffers: [],
      timerId: window.setInterval(() => {{
        void flushBrowserChunk();
      }}, Math.max(250, Math.round(chunkDurationSeconds * 1000))),
    }};
  }};

  const stopBrowserRecorder = async (
    {{ flushFinal, awaitUploads }} = {{ flushFinal: true, awaitUploads: true }},
  ) => {{
    const recorder = state.browserRecorder;
    if (!recorder) {{
      return;
    }}
    window.clearInterval(recorder.timerId);
    recorder.processor.onaudioprocess = null;
    try {{
      recorder.processor.disconnect();
    }} catch (_error) {{
      // Ignore disconnect failures during recorder cleanup.
    }}
    try {{
      recorder.captureGain.disconnect();
    }} catch (_error) {{
      // Ignore disconnect failures during recorder cleanup.
    }}
    if (state.visualizer?.captureProcessor === recorder.processor) {{
      state.visualizer.captureProcessor = null;
    }}
    if (state.visualizer?.captureGain === recorder.captureGain) {{
      state.visualizer.captureGain = null;
    }}
    const pendingBuffers = flushFinal ? recorder.buffers : [];
    recorder.buffers = [];
    state.browserRecorder = null;
    const uploadPromise = queueBrowserChunkUpload(pendingBuffers, recorder.sampleRate);
    if (awaitUploads) {{
      await uploadPromise;
    }}
  }};

  const refreshControls = () => {{
    sessionInput.disabled = state.busy || state.isRecording;
    modeSelect.disabled = state.busy || state.isRecording || state.isUploading || state.isProcessing;
    openStorageButton.disabled = state.busy || state.isRecording || state.isUploading || state.isProcessing;
    startButton.disabled = state.busy || state.isRecording || state.isUploading || state.isProcessing;
    stopButton.disabled = state.busy || !state.isRecording || state.isUploading || state.isProcessing;
    importButton.disabled = state.busy || state.isRecording || state.isUploading || state.isProcessing;
    closeButton.disabled = state.busy;
    openButton.disabled = state.busy;

    [startButton, stopButton, importButton, closeButton, openStorageButton].forEach((button) => {{
      button.style.opacity = button.disabled ? "0.6" : "1";
      button.style.cursor = button.disabled ? "not-allowed" : "pointer";
    }});

    openButton.style.opacity = state.busy ? "0.7" : "1";
    openButton.textContent = state.isRecording ? "Voice REC" : "Voice";
    openButton.style.background = state.isRecording ? "#b91c1c" : "#111827";
    openButton.style.boxShadow = state.isRecording
      ? "0 0 0 4px rgba(239, 68, 68, 0.18), 0 4px 14px rgba(0, 0, 0, 0.25)"
      : "0 4px 14px rgba(0, 0, 0, 0.25)";

    recordingDot.style.background = state.isRecording ? "#ef4444" : "#9ca3af";
    recordingDot.style.boxShadow = state.isRecording ? "0 0 0 6px rgba(239, 68, 68, 0.18)" : "none";
    recordingDot.style.animation = state.isRecording ? "strudelVoicePanelPulse 1.4s ease-out infinite" : "none";
    recordingText.textContent = state.isRecording ? "Grabando ahora" : "Listo para grabar";
    recordingText.style.color = state.isRecording ? "#b91c1c" : "#374151";
    recordingHint.textContent = state.isRecording
      ? "Microfono activo con monitoreo en tiempo real"
      : "El microfono espera la orden de inicio";
    recordingTimer.style.background = state.isRecording ? "#fee2e2" : "#e5e7eb";
    recordingTimer.style.color = state.isRecording ? "#b91c1c" : "#374151";
    visualizerCard.style.opacity = state.isRecording ? "1" : "0.65";

    const showProgressSpinner = state.isUploading || state.isProcessing;
    processingCard.style.background = showProgressSpinner ? "#eff6ff" : "#f9fafb";
    processingCard.style.borderColor = showProgressSpinner ? "#bfdbfe" : "#e5e7eb";
    processingSpinner.style.display = showProgressSpinner ? "block" : "none";
    processingTitle.textContent = state.isUploading
      ? "Subiendo audio"
      : state.isProcessing
        ? "Procesando audio"
        : "Palabras detectadas";
    processingTitle.style.color = showProgressSpinner ? "#1d4ed8" : "#374151";
    processingHint.textContent = state.isRecording
      ? "Cada bloque convertido va anadiendo palabras aqui en tiempo real."
      : state.isUploading
        ? "El ultimo bloque de audio se esta enviando al backend."
      : state.isProcessing
        ? "Terminando de cortar el audio y actualizando las palabras detectadas."
        : "Mientras grabas, aqui apareceran las palabras que ya se hayan convertido.";
    processingHint.style.color = showProgressSpinner ? "#1e40af" : "#6b7280";
    renderPreviewWords();
  }};

  const setBusy = (busy) => {{
    state.busy = busy;
    refreshControls();
  }};

  const updatePanelLayout = () => {{
    const compact = window.innerWidth < 980;
    contentLayout.style.gridTemplateColumns = compact ? "1fr" : "minmax(0, 1.05fr) minmax(0, 0.95fr)";
    rightColumn.style.marginTop = compact ? "0" : "0";
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
      throw new Error(await formatRuntimeErrorMessage(response));
    }}
    return response.json();
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
    let sessionStarted = false;
    let controlsReleased = false;
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      const runtime = await updateRuntimeInfo();
      const recorderBackend = runtime?.recorder?.effective_backend || runtime?.recorder?.configured_backend;
      if (runtime?.recorder && !runtime.recorder.ready) {{
        throw new Error(runtime.recorder.init_error || "El microfono no esta disponible en este equipo.");
      }}
      if (runtime?.transcriber && !runtime.transcriber.ready) {{
        throw new Error(runtime.transcriber.init_error || "El reconocimiento de voz no esta disponible.");
      }}
      if (recorderBackend === "browser") {{
        await startVisualizer();
      }}
      state.isUploading = false;
      state.isProcessing = false;
      state.previewWords = [];
      renderPreviewWords();
      setStatus("Iniciando grabacion...");
      await requestJson("/start", {{ session_id: sessionId }});
      sessionStarted = true;
      state.isRecording = true;
      startRecordingClock();
      startPreviewPolling();
      setBusy(false);
      controlsReleased = true;
      if (recorderBackend === "browser") {{
        await startBrowserRecorder();
        setStatus(`Grabacion iniciada: ${{sessionId}}. El navegador captura y envia el audio.`);
      }} else {{
        try {{
          await startVisualizer();
          setStatus(`Grabacion iniciada: ${{sessionId}}. Habla ahora para ver la senal.`);
        }} catch (_visualizerError) {{
          setStatus(`Grabacion iniciada: ${{sessionId}}. La vista del microfono no esta disponible en esta ventana.`);
        }}
      }}
    }} catch (error) {{
      try {{
        await stopBrowserRecorder({{ flushFinal: false, awaitUploads: false }});
      }} catch (_browserStopError) {{
        // Ignore cleanup errors after a failed start.
      }}
      await stopVisualizer();
      if (sessionStarted) {{
        try {{
          await requestJson("/stop", {{ session_id: state.sessionId }});
        }} catch (_stopAfterStartError) {{
          // Ignore stop failures after a failed browser start cleanup.
        }}
      }}
      state.isRecording = false;
      state.isUploading = false;
      state.isProcessing = false;
      stopRecordingClock();
      stopPreviewPolling();
      refreshControls();
      await updateRuntimeInfo();
      setStatus(`Error al iniciar: ${{String(error)}}`, true);
    }} finally {{
      if (!controlsReleased) {{
        setBusy(false);
      }}
    }}
  }});

  stopButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      const recorderBackend = state.runtimeDiagnostics?.recorder?.effective_backend
        || state.runtimeDiagnostics?.recorder?.configured_backend;
      state.isRecording = false;
      state.isUploading = recorderBackend === "browser";
      state.isProcessing = recorderBackend !== "browser";
      stopRecordingClock();
      let pendingBrowserUpload = Promise.resolve();
      if (recorderBackend === "browser") {{
        pendingBrowserUpload = stopBrowserRecorder({{ flushFinal: true, awaitUploads: false }});
      }}
      await stopVisualizer();
      startPreviewPolling();
      refreshControls();
      setStatus(
        recorderBackend === "browser"
          ? "Grabacion detenida. Subiendo el ultimo bloque de audio..."
          : "Grabacion detenida. Procesando en segundo plano; puedes cerrar la ventana.",
      );
      await pendingBrowserUpload;
      state.isUploading = false;
      state.isProcessing = true;
      refreshControls();
      setStatus("Audio subido. Procesando el audio en segundo plano; puedes cerrar la ventana.");
      await requestJson("/stop", {{ session_id: sessionId }});
      startStopPolling(sessionId);
    }} catch (error) {{
      state.isUploading = false;
      state.isProcessing = false;
      stopStopPolling();
      stopPreviewPolling();
      refreshControls();
      setStatus(`Error al detener: ${{String(error)}}`, true);
    }}
  }});

  importButton.addEventListener("click", async () => {{
    try {{
      const sessionId = normalizeSessionId();
      setBusy(true);
      const selectedMode = modeSelect.value;
      setStatus("Cargando muestras...");

      const response = await fetch(
        `${{state.baseUrl}}/samples/${{encodeURIComponent(sessionId)}}/manifest`,
      );
      if (!response.ok) {{
        throw new Error(`${{response.status}} — sesion no encontrada o sin muestras`);
      }}
      const manifest = await response.json();
      const items = manifest[selectedMode] || [];
      if (items.length === 0) {{
        throw new Error("No hay muestras disponibles. Graba primero y luego detén la sesion.");
      }}

      // Group by text so s('hola') cycles all recordings of that word.
      const sampleMap = {{}};
      for (const item of items) {{
        const key = (item.text || item.name).replace(/\\s+/g, "_").toLowerCase() || item.name;
        if (!sampleMap[key]) sampleMap[key] = [];
        sampleMap[key].push(item.url);
      }}

      const strudelSamples = window.strudelSamples;
      if (typeof strudelSamples !== "function") {{
        throw new Error("Strudel aun no esta listo. Espera a que cargue completamente.");
      }}
      await strudelSamples(sampleMap);

      const count = Object.keys(sampleMap).length;
      const label = modeSelect.options[modeSelect.selectedIndex].text;
      setStatus(`${{count}} muestras de ${{label}} listas. Usa s('nombre') en el editor.`);
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
    void updateRuntimeInfo();
    sessionInput.focus();
    sessionInput.select();
  }});

  sessionInput.addEventListener("input", () => {{
    updateStorageInfo();
    state.previewWords = [];
    renderPreviewWords();
  }});

  closeButton.addEventListener("click", () => {{
    overlay.style.display = "none";
  }});

  overlay.addEventListener("click", (event) => {{
    if (event.target === overlay) {{
      overlay.style.display = "none";
    }}
  }});

  window.addEventListener("beforeunload", () => {{
    stopStopPolling();
    stopPreviewPolling();
    stopRecordingClock();
    void stopBrowserRecorder({{ flushFinal: false, awaitUploads: false }});
    void stopVisualizer();
  }});
  window.addEventListener("resize", updatePanelLayout);

  actions.appendChild(startButton);
  actions.appendChild(stopButton);
  actions.appendChild(importButton);
  panel.appendChild(title);
  leftColumn.appendChild(stackSection([
    recordingState,
    modeLabel,
    modeSelect,
    actions,
    visualizerCard,
    status,
    closeButton,
  ]));
  rightColumn.appendChild(stackSection([
    inputLabel,
    sessionInput,
    storageLabel,
    storageInfo,
    openStorageButton,
    runtimeLabel,
    runtimeInfo,
    processingCard,
  ]));
  contentLayout.appendChild(leftColumn);
  contentLayout.appendChild(rightColumn);
  panel.appendChild(contentLayout);
  overlay.appendChild(panel);
  document.body.appendChild(openButton);
  document.body.appendChild(overlay);
  paintVisualizerIdle();
  setLevelMeter(0);
  updateRecordingClock();
  renderPreviewWords();
  updatePanelLayout();
  refreshControls();
  updateStorageInfo();
  void updateRuntimeInfo();
  return "installed";
}})();
"""
