# Form Testing Agent

This project provides a Python CLI for analyzing web forms, generating synthetic responses, and optionally submitting those responses to forms you own or are explicitly authorized to test.

It is designed for:

- QA testing
- survey dry-runs
- staging/demo environments
- generating datasets from form schemas

It is not designed to evade detection, impersonate real people, or mass-submit responses to third-party forms without permission.

## Fully Web Hosted

Yes. To run this without keeping any local terminal open, deploy it to an always-on web host.

The repo is now prepared for hosted deployment with:

- [Dockerfile](E:\codex gpt\Dockerfile)
- [.dockerignore](E:\codex gpt\.dockerignore)
- [wsgi.py](E:\codex gpt\wsgi.py)
- [Procfile](E:\codex gpt\Procfile)
- [render.yaml](E:\codex gpt\render.yaml)
- [railway.json](E:\codex gpt\railway.json)
- `gunicorn` in [requirements.txt](E:\codex gpt\requirements.txt)

The Docker image uses Microsoft's Playwright Python base image, which is much more reliable for browser automation in hosting environments.

## Production Hardening

The app now includes:

- a public `GET /health` endpoint that returns JSON status
- security headers on responses
- stricter cache behavior for authenticated pages
- activity logging for dashboard views, analyses, generations, submissions, downloads, and errors

Health endpoint example:

```text
https://your-service.example.com/health
```

Expected response shape:

```json
{
  "status": "ok",
  "service": "form-agent-studio",
  "timestamp": "2026-03-14T00:00:00+00:00",
  "auth_enabled": true,
  "output_dir": "/app/output"
}
```

## Render Deployment

This repo now includes a Docker-based [render.yaml](E:\codex gpt\render.yaml) tuned for Playwright hosting.

Recommended path:

1. Push this repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Let Render use [render.yaml](E:\codex gpt\render.yaml).
4. Set environment variables in Render:

```text
FORM_AGENT_USERNAME=your-username
FORM_AGENT_PASSWORD=your-strong-password
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

Render will build from the Dockerfile and expose the service with a public URL.

After redeploy, verify:

1. `https://your-service.onrender.com/health` returns `status: ok`
2. the main UI still loads behind auth
3. the help banner and recent activity panel are visible
4. activity log download still works

## Railway Deployment

This repo now includes [railway.json](E:\codex gpt\railway.json) and the shared [Dockerfile](E:\codex gpt\Dockerfile).

Recommended path:

1. Push this repo to GitHub.
2. Create a new Railway project from the repo.
3. Railway will detect [railway.json](E:\codex gpt\railway.json).
4. Set environment variables:

```text
FORM_AGENT_USERNAME=your-username
FORM_AGENT_PASSWORD=your-strong-password
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

Railway will build and run the Docker image, then give you a public domain.

## Hosting Notes

- The app now reads the hosting platform `PORT` environment variable automatically.
- Default host binding is now `0.0.0.0` for deployment friendliness.
- Activity logs are written to `output/activity_log.jsonl`; on ephemeral platforms this is best treated as temporary runtime storage unless you later add object storage or a database.

## Recommended Next Step

After pushing these changes, redeploy Render and verify `/health`. Then the next worthwhile upgrade is stronger auth or persistent storage for logs.
