import time

import requests

from joulie import config


class Agent:
    def __init__(
        self,
        model: str = config.OLLAMA_MODEL,
        url: str = config.OLLAMA_URL,
        system_prompt: str = config.SYSTEM_PROMPT,
    ):
        self.model = model
        self.url = url.rstrip("/")
        self.system_prompt = system_prompt
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

    def reply(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": self.system_prompt}, *self.history]
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
