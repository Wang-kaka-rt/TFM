import { NestFactory } from "@nestjs/core";

import { AppModule } from "./app.module";

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule, {
    cors: {
      origin: ["http://127.0.0.1:3000", "http://localhost:3000", "https://strudel.cc"],
      credentials: true,
    },
  });

  const port = Number(process.env.PORT ?? 3000);
  await app.listen(port, "127.0.0.1");
}

void bootstrap();
