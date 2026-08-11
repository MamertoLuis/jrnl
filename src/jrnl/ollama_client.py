from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class OllamaClient:
    host: str
    timeout_seconds: int = 30

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.host, timeout=self.timeout_seconds)

    def generate(self, model: str, prompt: str, *, format: str | None = None) -> str:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if format is not None:
            payload["format"] = format
        with self._client() as client:
            response = client.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        payload = {"model": model, "messages": messages, "stream": False}
        with self._client() as client:
            response = client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
