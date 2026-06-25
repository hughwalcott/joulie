import json
import time
from collections.abc import Iterator

import requests

from joulie import config


class Agent:
    def __init__(
        self,
        model: str = config.OLLAMA_MODEL,
        url: str = config.OLLAMA_URL,
        system_prompt: str = config.SYSTEM_PROMPT,
        retriever=None,
    ):
        self.model = model
        self.url = url.rstrip("/")
        self.system_prompt = system_prompt
        self.retriever = retriever
        self.history: list[dict] = []

    def reset(self):
        self.history = []

    def warmup(self) -> float:
        """Force Ollama to load weights + compile Metal shaders. Returns seconds."""
        start = time.monotonic()
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": "ok"}],
                "stream": False,
                "options": {"num_predict": 1},
            },
            timeout=180,
        )
        resp.raise_for_status()
        return time.monotonic() - start

    def _build_messages(self, user_text: str) -> list[dict]:
        context_msg = None
        if self.retriever is not None:
            chunks = self.retriever.retrieve(user_text)
            if chunks:
                context_block = self.retriever.format_context(chunks)
                sources = ", ".join(sorted({c["source"] for c in chunks}))
                print(f"[rag] injected {len(chunks)} chunks from: {sources}")
                context_msg = {
                    "role": "system",
                    "content": (
                        "Relevant reference material from the New Zealand electrification "
                        "knowledge base:\n\n"
                        f"{context_block}\n\n"
                        "Use this material to inform your answer when relevant. "
                        "Cite the source document and page number where you draw on it."
                    ),
                }
        self.history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": self.system_prompt}]
        if context_msg is not None:
            messages.append(context_msg)
        messages.extend(self.history)
        return messages

    def stream(self, user_text: str) -> Iterator[str]:
        """Yield text tokens from Ollama as they arrive. Updates history when exhausted."""
        messages = self._build_messages(user_text)
        resp = requests.post(
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": True},
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        accumulated: list[str] = []
        try:
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                data = json.loads(raw_line)
                token = data.get("message", {}).get("content", "")
                if token:
                    accumulated.append(token)
                    yield token
                if data.get("done"):
                    break
        finally:
            full_text = "".join(accumulated).strip()
            if full_text:
                self.history.append({"role": "assistant", "content": full_text})

    def reply(self, user_text: str) -> str:
        messages = self._build_messages(user_text)
        resp = requests.post(
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        self.history.append({"role": "assistant", "content": text})
        return text
