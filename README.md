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

## Best Option

For "fully on web without terminals open", the best option is a cloud host such as Render or Railway.

Why this is better than a local tunnel:

- no PC needs to stay on
- no local terminal needs to stay open
- public URL stays up independently
- easier to manage auth and redeploys

## Docker Deployment

Build locally:

```powershell
docker build -t form-agent-studio .
```

Run locally:

```powershell
docker run -p 8000:8000 -e FORM_AGENT_USERNAME=admin -e FORM_AGENT_PASSWORD=change-me-now form-agent-studio
```

The container starts with:

```text
gunicorn --bind 0.0.0.0:8000 wsgi:app
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

## Sources

- [Render Flask quickstart](https://render.com/docs/deploy-flask)
- [Render web services docs](https://render.com/docs/web-services)
- [Railway Flask guide](https://docs.railway.com/guides/flask)
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/)
- [Cloudflare named tunnel config](https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/)
- [Cloudflare run as a Windows service](https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/windows/)

## Recommended Next Step

If you want the smoothest deployment path from here, Render is the simplest first target and Railway is a solid second option.
