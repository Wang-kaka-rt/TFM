import { Injectable } from "@nestjs/common";

import type { BackendResponse, SessionPayload } from "./dto/session.dto";

@Injectable()
export class StrudelService {
  private readonly backendBaseUrl =
    process.env.PYTHON_BACKEND_URL ?? "http://127.0.0.1:8787";

  health(): Promise<BackendResponse> {
    return this.request<BackendResponse>("/health", {
      method: "GET",
    });
  }

  start(payload: SessionPayload): Promise<BackendResponse> {
    return this.request<BackendResponse>("/start", {
      method: "POST",
      body: JSON.stringify({ session_id: payload.sessionId }),
    });
  }

  reload(payload: SessionPayload): Promise<BackendResponse> {
    return this.request<BackendResponse>("/reload", {
      method: "POST",
      body: JSON.stringify({ session_id: payload.sessionId }),
    });
  }

  stop(payload: SessionPayload): Promise<BackendResponse> {
    return this.request<BackendResponse>("/stop", {
      method: "POST",
      body: JSON.stringify({ session_id: payload.sessionId }),
    });
  }

  status(sessionId?: string): Promise<BackendResponse> {
    const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return this.request<BackendResponse>(`/status${suffix}`, {
      method: "GET",
    });
  }

  metrics(): Promise<Record<string, number>> {
    return this.request<Record<string, number>>("/metrics", {
      method: "GET",
    });
  }

  samplesManifest(sessionId: string): Promise<BackendResponse> {
    return this.request<BackendResponse>(`/samples/${encodeURIComponent(sessionId)}/manifest`, {
      method: "GET",
    });
  }

  metadata(sessionId: string): Promise<BackendResponse> {
    return this.request<BackendResponse>(`/metadata/${encodeURIComponent(sessionId)}`, {
      method: "GET",
    });
  }

  async strudelScript(sessionId: string): Promise<string> {
    const response = await fetch(
      `${this.backendBaseUrl}/strudel/${encodeURIComponent(sessionId)}`,
      { method: "GET" },
    );
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Backend request failed: ${response.status} ${body}`);
    }
    return response.text();
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetch(`${this.backendBaseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Backend request failed: ${response.status} ${body}`);
    }

    return (await response.json()) as T;
  }
}
