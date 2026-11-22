"""Async Ollama client for model discovery and streaming generation."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import AsyncGenerator, Dict, List, Optional


class OllamaClient:
    """Communicates with local Ollama server."""

    def __init__(self, host: Optional[str] = None) -> None:
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.host}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_local_models(self) -> List[Dict[str, str]]:
        """Fetch list of models currently pulled in Ollama."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = []
                for m in data.get("models", []):
                    models.append({
                        "name": m.get("name", ""),
                        "size": f"{round(m.get('size', 0) / (1024**3), 1)}GB",
                        "modified_at": m.get("modified_at", ""),
                    })
                return models
        except Exception:
            return []

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Asynchronously streams response tokens from Ollama."""
        import asyncio

        url = f"{self.host}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        def _fetch_stream():
            try:
                return urllib.request.urlopen(req, timeout=120)
            except urllib.error.URLError as e:
                raise RuntimeError(f"Failed to connect to Ollama ({self.host}): {e}")

        # Run connection synchronously in thread
        resp = await asyncio.to_thread(_fetch_stream)

        loop = asyncio.get_event_loop()

        def _read_line():
            return resp.readline()

        try:
            while True:
                line = await loop.run_in_executor(None, _read_line)
                if not line:
                    break
                decoded = line.decode("utf-8").strip()
                if not decoded:
                    continue
                try:
                    obj = json.loads(decoded)
                    chunk = obj.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if obj.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        finally:
            resp.close()
