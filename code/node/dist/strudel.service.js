"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.StrudelService = void 0;
const common_1 = require("@nestjs/common");
let StrudelService = class StrudelService {
    backendBaseUrl = process.env.PYTHON_BACKEND_URL ?? "http://127.0.0.1:8787";
    health() {
        return this.request("/health", {
            method: "GET",
        });
    }
    start(payload) {
        return this.request("/start", {
            method: "POST",
            body: JSON.stringify({ session_id: payload.sessionId }),
        });
    }
    reload(payload) {
        return this.request("/reload", {
            method: "POST",
            body: JSON.stringify({ session_id: payload.sessionId }),
        });
    }
    stop(payload) {
        return this.request("/stop", {
            method: "POST",
            body: JSON.stringify({ session_id: payload.sessionId }),
        });
    }
    status(sessionId) {
        const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
        return this.request(`/status${suffix}`, {
            method: "GET",
        });
    }
    metrics() {
        return this.request("/metrics", {
            method: "GET",
        });
    }
    samplesManifest(sessionId) {
        return this.request(`/samples/${encodeURIComponent(sessionId)}/manifest`, {
            method: "GET",
        });
    }
    metadata(sessionId) {
        return this.request(`/metadata/${encodeURIComponent(sessionId)}`, {
            method: "GET",
        });
    }
    async strudelScript(sessionId) {
        const response = await fetch(`${this.backendBaseUrl}/strudel/${encodeURIComponent(sessionId)}`, { method: "GET" });
        if (!response.ok) {
            const body = await response.text();
            throw new Error(`Backend request failed: ${response.status} ${body}`);
        }
        return response.text();
    }
    async request(path, init) {
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
        return (await response.json());
    }
};
exports.StrudelService = StrudelService;
exports.StrudelService = StrudelService = __decorate([
    (0, common_1.Injectable)()
], StrudelService);
//# sourceMappingURL=strudel.service.js.map