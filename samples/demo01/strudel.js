const STRUDEL_VOICE = {
  "sessionId": "demo01",
  "samples": {
    "words": [],
    "phrases": [],
    "sentences": [],
    "letters": []
  }
};

export const strudelVoiceSession = STRUDEL_VOICE.sessionId;
export const strudelVoiceSamples = STRUDEL_VOICE.samples;
export async function start(sessionId) {
  const response = await fetch('http://127.0.0.1:8787/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return response.json();
}
export async function stop(sessionId) {
  const response = await fetch('http://127.0.0.1:8787/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return response.json();
}
