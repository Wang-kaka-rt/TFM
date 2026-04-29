import {
  BadRequestException,
  Body,
  Controller,
  Get,
  Post,
  Query,
} from "@nestjs/common";

import type { BackendResponse, SessionPayload } from "./dto/session.dto";
import { StrudelService } from "./strudel.service";

@Controller()
export class AppController {
  constructor(private readonly strudelService: StrudelService) {}

  private requireSessionId(sessionId?: string): string {
    if (!sessionId) {
      throw new BadRequestException("sessionId is required");
    }
    return sessionId;
  }

  @Get("health")
  getHealth(): Promise<BackendResponse> {
    return this.strudelService.health();
  }

  @Post("strudel/start")
  start(@Body() payload: SessionPayload): Promise<BackendResponse> {
    return this.strudelService.start(payload);
  }

  @Post("strudel/reload")
  reload(@Body() payload: SessionPayload): Promise<BackendResponse> {
    return this.strudelService.reload(payload);
  }

  @Post("strudel/stop")
  stop(@Body() payload: SessionPayload): Promise<BackendResponse> {
    return this.strudelService.stop(payload);
  }

  @Get("strudel/status")
  status(@Query("sessionId") sessionId?: string): Promise<BackendResponse> {
    return this.strudelService.status(sessionId);
  }

  @Get("strudel/metrics")
  metrics(): Promise<Record<string, number>> {
    return this.strudelService.metrics();
  }

  @Get("strudel/samples")
  samples(@Query("sessionId") sessionId?: string): Promise<BackendResponse> {
    return this.strudelService.samplesManifest(this.requireSessionId(sessionId));
  }

  @Get("strudel/metadata")
  metadata(@Query("sessionId") sessionId?: string): Promise<BackendResponse> {
    return this.strudelService.metadata(this.requireSessionId(sessionId));
  }

  @Get("strudel/script")
  async script(@Query("sessionId") sessionId?: string): Promise<{ script: string }> {
    return { script: await this.strudelService.strudelScript(this.requireSessionId(sessionId)) };
  }
}
