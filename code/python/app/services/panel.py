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
