import { Module } from "@nestjs/common";

import { AppController } from "./app.controller";
import { StrudelService } from "./strudel.service";

@Module({
  imports: [],
  controllers: [AppController],
  providers: [StrudelService],
})
export class AppModule {}
