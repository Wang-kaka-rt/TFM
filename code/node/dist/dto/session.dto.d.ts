export interface SessionPayload {
    sessionId: string;
}
export interface BackendResponse<T = unknown> {
    ok: boolean;
    message: string;
    session?: T;
    active_session?: T | null;
    sessions?: T[];
}
