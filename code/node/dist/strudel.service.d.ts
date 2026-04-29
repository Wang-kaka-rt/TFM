import type { BackendResponse, SessionPayload } from "./dto/session.dto";
export declare class StrudelService {
    private readonly backendBaseUrl;
    health(): Promise<BackendResponse>;
    start(payload: SessionPayload): Promise<BackendResponse>;
    reload(payload: SessionPayload): Promise<BackendResponse>;
    stop(payload: SessionPayload): Promise<BackendResponse>;
    status(sessionId?: string): Promise<BackendResponse>;
    metrics(): Promise<Record<string, number>>;
    samplesManifest(sessionId: string): Promise<BackendResponse>;
    metadata(sessionId: string): Promise<BackendResponse>;
    strudelScript(sessionId: string): Promise<string>;
    private request;
}
