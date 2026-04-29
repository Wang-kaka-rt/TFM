"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const core_1 = require("@nestjs/core");
const app_module_1 = require("./app.module");
async function bootstrap() {
    const app = await core_1.NestFactory.create(app_module_1.AppModule, {
        cors: {
            origin: ["http://127.0.0.1:3000", "http://localhost:3000", "https://strudel.cc"],
            credentials: true,
        },
    });
    const port = Number(process.env.PORT ?? 3000);
    await app.listen(port, "127.0.0.1");
}
void bootstrap();
//# sourceMappingURL=main.js.map