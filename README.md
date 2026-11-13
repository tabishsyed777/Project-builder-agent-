# Forge — Local Project Builder Agent

Forge is a local-first project assistant. Type a question or project command in the chat panel and Forge sends it to an Ollama model running on your computer. A small Python API keeps the model connection private to your machine and reports whether Ollama and Docker are ready.

The current build is an early working foundation. Chat is connected to Ollama. Docker tasks are isolated and require explicit confirmation, but the chat model does not yet automatically turn arbitrary natural-language requests into Docker actions or edit a persistent project workspace.

## What works

- Local chat through Ollama's `/api/chat` endpoint
- Live status for Ollama, the configured model, and Docker
- Browser chat interface served by the Python API
- Docker task API with exact command preview and an explicit confirmation step
- Docker limits: temporary workspace, no network, read-only container root, dropped capabilities, resource limits, and a 120-second timeout
- Existing project brief planner and draft-file generator

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- Docker Desktop installed and running (needed only for container tasks)
- A model available to Ollama; default is `qwen2.5-coder:3b`

On an 8 GB machine, use a small quantized model and close other memory-heavy apps. The configured model can be changed with `OLLAMA_MODEL`.

## Start Forge

In Terminal, from this project folder:

```sh
ollama pull qwen2.5-coder:3b
ollama serve
```

In a second Terminal window, start Docker Desktop, then run:

```sh
python3 server.py
```

Open <http://127.0.0.1:8765>. Keep the server running while using Forge. The UI needs to be opened through this local server; opening `index.html` directly will not connect to the API.

Optional settings:

```sh
OLLAMA_MODEL=qwen2.5-coder:3b OLLAMA_URL=http://127.0.0.1:11434 FORGE_PORT=8765 python3 server.py
```

## Docker task safety

Forge never runs a task just because a model suggested it. A task must be submitted through the task API and the user must confirm the displayed image and argument list. Only `python:3.12-alpine` and `node:22-alpine` are currently accepted. Containers have no network and use an empty temporary working directory. Do not put secrets in prompts or generated commands.

## Current limitations

- The model answers chat requests; automatic tool planning and natural-language-to-Docker execution are not implemented yet.
- Docker tasks currently start with an empty temporary folder. They cannot modify a persistent project checkout.
- The generated planner output remains a deterministic template, not an LLM-generated plan.
- Docker execution cannot be verified until Docker Desktop is running and an image is available locally or can be pulled.
- There is no authentication. The API binds to `127.0.0.1` by default; do not expose it to a network without adding authentication and reviewing the security model.

## Files

- `index.html` — Forge interface and existing plan builder
- `server.py` — local Ollama and Docker API
- `README.md` — setup and project notes

## License

See [LICENSE](LICENSE).
