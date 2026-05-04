# AHAL AI Deployment

## Local Python Run

Run the API directly:

```bash
python -m app.main
```

The API starts on `http://localhost:8000` by default.

## Docker Run

Build the image:

```bash
docker build -t ahal-ai .
```

Run the container:

```bash
docker run --rm -p 8000:8000 --env-file .env ahal-ai
```

## Docker Compose Run

Start the default memory-backed stack:

```bash
docker compose up --build
```

The default compose setup keeps:

- `AHAL_STORAGE_BACKEND=memory`
- `AHAL_LLM_ENABLED=false`
- no MongoDB dependency unless the Mongo profile is enabled
- GitHub webhooks disabled unless you opt in with `AHAL_GITHUB_WEBHOOK_ENABLED=true`

## Optional Gemini Setup

1. Copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY=`.
3. Change `AHAL_LLM_ENABLED=true` only when you want optional LLM features enabled.

AHAL still runs without Gemini.

## Optional Mongo Profile

MongoDB is optional. To bring it up with Docker Compose:

```bash
docker compose --profile mongo up --build
```

If you enable Mongo later, set:

```env
AHAL_STORAGE_BACKEND=mongodb
MONGODB_URI=mongodb://mongo:27017
MONGODB_DB=ahal_ai
AHAL_SESSION_TTL_HOURS=24
```

Memory mode remains the default in this phase.

## Webhook Enablement

GitHub webhook handling is optional and does not require a GitHub token in this phase.

Set the following only when you want AHAL to receive webhook events:

```env
AHAL_GITHUB_WEBHOOK_ENABLED=true
AHAL_GITHUB_WEBHOOK_SECRET=your_shared_secret
```

The webhook endpoint is:

```text
POST /webhooks/github
```

If you configure a secret, AHAL verifies `X-Hub-Signature-256` before it accepts the payload.

## MCP Server Command

Run the MCP stdio server locally with:

```bash
python -m app.mcp.server
```

## Healthcheck

The API exposes:

```text
GET /health
```

Docker uses this endpoint for container health checks.

## Common Troubleshooting

- If uploads fail, verify port `8000` is available and the container can write temporary files.
- If optional Gemini features do not activate, confirm `AHAL_LLM_ENABLED=true` and that `GEMINI_API_KEY` is set in your local `.env`.
- If Docker Compose starts without MongoDB, that is expected unless you enable the `mongo` profile.
- If you turn on MongoDB mode without a Mongo-compatible client installed, AHAL will fail clearly instead of silently switching storage behavior.
- If webhook requests are rejected, confirm `AHAL_GITHUB_WEBHOOK_ENABLED=true` and that your GitHub webhook secret matches `AHAL_GITHUB_WEBHOOK_SECRET`.
- On Windows, you can still use the local workflow with `python -m app.main` if Docker is not available.
