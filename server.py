"""Forge local agent API: Ollama chat plus explicitly scoped Docker tasks."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = os.getenv("FORGE_HOST", "127.0.0.1")
PORT = int(os.getenv("FORGE_PORT", "8765"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
TASKS: dict[str, dict] = {}
LOCK = threading.Lock()
SYSTEM = """You are Forge, a practical project-building assistant running locally for one developer. Answer in the user's language. Be concise, ask only essential clarifying questions, state assumptions, and never claim a command ran unless the tool result confirms it. Help plan, write, debug, and explain projects. Docker actions run in isolated temporary containers with a read-only root filesystem, no network, dropped Linux capabilities, resource limits, and an ephemeral workspace; do not request secrets. When the user asks you to execute a project task, explain the planned command and obtain an explicit UI confirmation before running it. Do not fabricate test results."""


def docker_status() -> dict:
    if not shutil.which("docker"):
        return {"available": False, "detail": "Docker CLI not installed"}
    try:
        p = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=4)
        return {"available": p.returncode == 0, "detail": p.stdout.strip() if p.returncode == 0 else (p.stderr.strip()[-240:] or "Docker daemon unavailable")}
    except Exception as exc:
        return {"available": False, "detail": str(exc)}


def ollama_status() -> dict:
    try:
        with urllib.request.urlopen(OLLAMA_URL.rstrip("/") + "/api/tags", timeout=2) as res:
            models = json.load(res).get("models", [])
            names = [m.get("name", "") for m in models]
            return {"available": True, "model": MODEL, "model_installed": any(n == MODEL or n.startswith(MODEL + ":") for n in names), "models": names}
    except Exception as exc:
        return {"available": False, "model": MODEL, "detail": str(exc)}


def send_json(handler, status, data):
    raw = json.dumps(data).encode()
    handler.send_response(status); handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw))); handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type"); handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers(); handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_OPTIONS(self): send_json(self, 204, {})
    def do_GET(self):
        if self.path == "/api/status":
            send_json(self, 200, {"ollama": ollama_status(), "docker": docker_status(), "model": MODEL})
        elif self.path.startswith("/api/task/"):
            with LOCK: task = TASKS.get(self.path.rsplit("/", 1)[-1])
            send_json(self, 200 if task else 404, task or {"error": "Task not found"})
        elif self.path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        else: send_json(self, 404, {"error": "Not found"})
    def body(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n > 100_000: raise ValueError("Request too large")
        return json.loads(self.rfile.read(n) or b"{}")
    def do_POST(self):
        try:
            data = self.body()
            if self.path == "/api/chat": self.chat(data)
            elif self.path == "/api/task": self.start_task(data)
            elif self.path.startswith("/api/task/") and self.path.endswith("/confirm"): self.confirm_task(data, self.path.split("/")[-2])
            else: send_json(self, 404, {"error": "Not found"})
        except ValueError as exc: send_json(self, 400, {"error": str(exc)})
        except Exception as exc: send_json(self, 500, {"error": str(exc)})
    def chat(self, data):
        messages = data.get("messages", [])
        if not messages or len(messages) > 30: return send_json(self, 400, {"error": "Provide 1–30 chat messages"})
        payload = json.dumps({"model": MODEL, "stream": False, "messages": [{"role": "system", "content": SYSTEM}] + [{"role": m.get("role"), "content": str(m.get("content", ""))[:12000]} for m in messages if m.get("role") in ("user", "assistant")]}).encode()
        req = urllib.request.Request(OLLAMA_URL.rstrip("/") + "/api/chat", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as res: answer = json.load(res).get("message", {}).get("content", "")
            send_json(self, 200, {"answer": answer, "model": MODEL})
        except urllib.error.URLError as exc: send_json(self, 503, {"error": f"Ollama is not reachable at {OLLAMA_URL}. Start Ollama and install {MODEL}.", "detail": str(exc)})
    def start_task(self, data):
        command = data.get("command")
        if not isinstance(command, list) or not command or len(command) > 20 or any(not isinstance(x, str) or len(x) > 500 for x in command): return send_json(self, 400, {"error": "command must be a short array of arguments"})
        if not docker_status()["available"]: return send_json(self, 503, {"error": "Docker daemon is unavailable"})
        image = data.get("image", "python:3.12-alpine")
        if image not in ("python:3.12-alpine", "node:22-alpine"): return send_json(self, 400, {"error": "Image is not in Forge's allowed image list"})
        task_id = str(int(time.time() * 1000));
        with LOCK: TASKS[task_id] = {"id": task_id, "status": "awaiting_confirmation", "image": image, "command": command, "created": int(time.time())}
        send_json(self, 201, TASKS[task_id])
    def confirm_task(self, data, task_id):
        with LOCK: task = TASKS.get(task_id)
        if not task: return send_json(self, 404, {"error": "Task not found"})
        if data.get("confirmed") is not True: return send_json(self, 400, {"error": "Explicit confirmation required"})
        if task["status"] != "awaiting_confirmation": return send_json(self, 409, {"error": "Task already confirmed or run"})
        task["status"] = "running"
        try:
            with tempfile.TemporaryDirectory(prefix="forge-task-") as work:
                args = ["docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=768m", "--cpus=1", "--pids-limit=128", "--tmpfs=/tmp:rw,noexec,nosuid,size=64m", "-v", f"{work}:/workspace:rw", "-w", "/workspace", task["image"], *task["command"]]
                p = subprocess.run(args, capture_output=True, text=True, timeout=120)
                task.update(status="succeeded" if p.returncode == 0 else "failed", exit_code=p.returncode, stdout=p.stdout[-12000:], stderr=p.stderr[-12000:])
        except subprocess.TimeoutExpired: task.update(status="timed_out", stderr="Task exceeded 120 seconds")
        except Exception as exc: task.update(status="failed", stderr=str(exc))
        send_json(self, 200, task)


if __name__ == "__main__":
    print(f"Forge API listening at http://{HOST}:{PORT} (model={MODEL})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
