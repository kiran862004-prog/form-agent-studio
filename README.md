# Form Testing Agent

This project provides a Python CLI for analyzing web forms, generating synthetic responses, and optionally submitting those responses to forms you own or are explicitly authorized to test.

It is designed for:

- QA testing
- survey dry-runs
- staging/demo environments
- generating datasets from form schemas

It is not designed to evade detection, impersonate real people, or mass-submit responses to third-party forms without permission.

## Current Deployment Note

The hosted app uses a Playwright-pinned Docker image and Python package version to keep browser automation stable in production.

Current aligned version:

- Docker image: `mcr.microsoft.com/playwright/python:v1.58.0-jammy`
- Python package: `playwright==1.58.0`

If you ever update Playwright again, update both [Dockerfile](E:\codex gpt\Dockerfile) and [requirements.txt](E:\codex gpt\requirements.txt) together.

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

## Recommended Next Step

After pushing changes, redeploy Render and verify both `/health` and a live browser-backed action such as form analysis.
