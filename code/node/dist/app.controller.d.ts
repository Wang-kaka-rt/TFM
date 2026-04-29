import type { BackendResponse, SessionPayload } from "./dto/session.dto";
import { StrudelService } from "./strudel.service";
export declare class AppController {
    private readonly strudelService;
    constructor(strudelService: StrudelService);
    private requireSessionId;
    getHealth(): Promise<BackendResponse>;
    start(payload: SessionPayload): Promise<BackendResponse>;
    reload(payload: SessionPayload): Promise<BackendResponse>;
    stop(payload: SessionPayload): Promise<BackendResponse>;
    status(sessionId?: string): Promise<BackendResponse>;
    metrics(): Promise<Record<string, number>>;
    samples(sessionId?: string): Promise<BackendResponse>;
    metadata(sessionId?: string): Promise<BackendResponse>;
    script(sessionId?: string): Promise<{
        script: string;
    }>;
}
