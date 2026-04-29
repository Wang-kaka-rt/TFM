# Strudel Voice Node Bridge

## Current scope
- Sprint 0 integration scaffold
- NestJS bridge service
- Proxy endpoints for `start`, `reload`, `stop`, `status`
- Artifact and metrics proxy: script, samples, metadata, metrics

## Run
```bash
npm install
npm run start:dev
```

## Environment
- `PYTHON_BACKEND_URL=http://127.0.0.1:8787`
- `PORT=3000`
- Copy `.env.example` to `.env` if you prefer local env file management.

## Available endpoints
- `GET /health`
- `POST /strudel/start`
- `POST /strudel/reload`
- `POST /strudel/stop`
- `GET /strudel/status`
- `GET /strudel/metrics`
- `GET /strudel/script?sessionId=...`
- `GET /strudel/samples?sessionId=...`
- `GET /strudel/metadata?sessionId=...`
