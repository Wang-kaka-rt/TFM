const baseUrl = process.env.NODE_BRIDGE_URL ?? "http://127.0.0.1:3000";

async function call(path, payload) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${await response.text()}`);
  }

  return response.json();
}

export async function start(sessionId) {
  return call("/strudel/start", { sessionId });
}

export async function reload(sessionId) {
  return call("/strudel/reload", { sessionId });
}

export async function stop(sessionId) {
  return call("/strudel/stop", { sessionId });
}
