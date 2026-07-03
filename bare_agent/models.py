from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


class ModelError(RuntimeError):
    pass


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        raise NotImplementedError


@dataclass
class OpenAIChatClient:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 45

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ModelError(
                f"OpenAI API returned HTTP {exc.code}. Check OPENAI_MODEL, OPENAI_BASE_URL, "
                f"and key permissions. Response: {error_body[:800]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ModelError(
                f"Could not reach the LLM API. Check network access and OPENAI_BASE_URL. {exc}"
            ) from exc

        try:
            decoded = json.loads(body)
            return str(decoded["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ModelError(f"Unexpected LLM response shape: {body[:800]}") from exc


@dataclass
class ScriptedModel:
    responses: list[str]
    requests: list[list[dict[str, str]]] = field(default_factory=list)

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.requests.append([dict(message) for message in messages])
        if not self.responses:
            return json.dumps(
                {
                    "type": "final",
                    "summary": "The scripted model ran out of planned steps.",
                    "next_steps": ["Add another scripted response for this scenario."],
                }
            )
        return self.responses.pop(0)

