"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AppController = void 0;
const common_1 = require("@nestjs/common");
const strudel_service_1 = require("./strudel.service");
let AppController = class AppController {
    strudelService;
    constructor(strudelService) {
        this.strudelService = strudelService;
    }
    requireSessionId(sessionId) {
        if (!sessionId) {
            throw new common_1.BadRequestException("sessionId is required");
        }
        return sessionId;
    }
    getHealth() {
        return this.strudelService.health();
    }
    start(payload) {
        return this.strudelService.start(payload);
    }
    reload(payload) {
        return this.strudelService.reload(payload);
    }
    stop(payload) {
        return this.strudelService.stop(payload);
    }
    status(sessionId) {
        return this.strudelService.status(sessionId);
    }
    metrics() {
        return this.strudelService.metrics();
    }
    samples(sessionId) {
        return this.strudelService.samplesManifest(this.requireSessionId(sessionId));
    }
    metadata(sessionId) {
        return this.strudelService.metadata(this.requireSessionId(sessionId));
    }
    async script(sessionId) {
        return { script: await this.strudelService.strudelScript(this.requireSessionId(sessionId)) };
    }
};
exports.AppController = AppController;
__decorate([
    (0, common_1.Get)("health"),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Promise)
], AppController.prototype, "getHealth", null);
__decorate([
    (0, common_1.Post)("strudel/start"),
    __param(0, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "start", null);
__decorate([
    (0, common_1.Post)("strudel/reload"),
    __param(0, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "reload", null);
__decorate([
    (0, common_1.Post)("strudel/stop"),
    __param(0, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "stop", null);
__decorate([
    (0, common_1.Get)("strudel/status"),
    __param(0, (0, common_1.Query)("sessionId")),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "status", null);
__decorate([
    (0, common_1.Get)("strudel/metrics"),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Promise)
], AppController.prototype, "metrics", null);
__decorate([
    (0, common_1.Get)("strudel/samples"),
    __param(0, (0, common_1.Query)("sessionId")),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "samples", null);
__decorate([
    (0, common_1.Get)("strudel/metadata"),
    __param(0, (0, common_1.Query)("sessionId")),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "metadata", null);
__decorate([
    (0, common_1.Get)("strudel/script"),
    __param(0, (0, common_1.Query)("sessionId")),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", Promise)
], AppController.prototype, "script", null);
exports.AppController = AppController = __decorate([
    (0, common_1.Controller)(),
    __metadata("design:paramtypes", [strudel_service_1.StrudelService])
], AppController);
//# sourceMappingURL=app.controller.js.map