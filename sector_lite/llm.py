"""Client LLM minimi e intercambiabili: Gemini, Anthropic, endpoint compatibili OpenAI (Ollama, vLLM...).
Interfaccia unica: client.label e client.complete(system, user) -> str. SDK importati solo se usati."""
from __future__ import annotations

import json
import random
import re
import time
from typing import Callable, Optional, Protocol, Sequence, Union


class LLMClient(Protocol):
    label: str

    def complete(self, system: str, user: str) -> str: ...


PERMANENT_STATUS = (400, 401, 403, 404, 422)  # chiave errata, crediti finiti, modello inesistente: inutile riprovare


def with_retries(fn: Callable, *, attempts: int = 4, base_delay: float = 1.0, max_delay: float = 20.0):
    """Backoff esponenziale con jitter su qualsiasi errore, tranne quelli permanenti (status HTTP in PERMANENT_STATUS)."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            status = getattr(e, "status_code", None) or getattr(e, "code", None)
            if (isinstance(status, int) and status in PERMANENT_STATUS) or i == attempts - 1:
                break
            time.sleep(min(max_delay, base_delay * 2**i) * (0.5 + random.random()))
    raise last


class GeminiClient:
    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None,
                 temperature: Optional[float] = 0.0, label: Optional[str] = None):
        from google import genai

        self.model, self.temperature = model, temperature
        self.label = label or f"gemini:{model}"
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def complete(self, system: str, user: str) -> str:
        from google.genai import types

        cfg = types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                          temperature=self.temperature)
        return self._client.models.generate_content(model=self.model, contents=user, config=cfg).text or ""


class AnthropicClient:
    """temperature=None (default): non viene inviata (alcuni modelli recenti non accettano parametri di campionamento)."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", api_key: Optional[str] = None,
                 temperature: Optional[float] = None, max_tokens: int = 1024, label: Optional[str] = None):
        import anthropic

        self.model, self.temperature, self.max_tokens = model, temperature, max_tokens
        self.label = label or f"anthropic:{model}"
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def complete(self, system: str, user: str) -> str:
        kw = dict(model=self.model, max_tokens=self.max_tokens, system=system,
                  messages=[{"role": "user", "content": user}])
        if self.temperature is not None:
            kw["temperature"] = self.temperature
        msg = self._client.messages.create(**kw)
        return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")


class OpenAICompatClient:
    """Ollama ('http://localhost:11434/v1'), vLLM, llama.cpp, LM Studio (json_mode=False), OpenAI..."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 temperature: Optional[float] = 0.0, json_mode: bool = True, label: Optional[str] = None):
        from openai import OpenAI

        self.model, self.temperature, self.json_mode = model, temperature, json_mode
        self.label = label or f"openai-compat:{model}"
        self._client = OpenAI(api_key=api_key or "not-needed", base_url=base_url)

    def complete(self, system: str, user: str) -> str:
        kw = dict(model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        if self.temperature is not None:
            kw["temperature"] = self.temperature
        if self.json_mode:
            kw["response_format"] = {"type": "json_object"}
        return self._client.chat.completions.create(**kw).choices[0].message.content or ""


class ScriptedClient:
    """Modello finto per test e demo offline. responses: str o callable(system, user) o lista di essi
    (l'ultimo si ripete). Registra le chiamate in .calls."""

    def __init__(self, label: str, responses: Union[str, Callable, Sequence]):
        self.label = label
        self.responses = [responses] if (isinstance(responses, str) or callable(responses)) else list(responses)
        self.calls: list = []

    def complete(self, system: str, user: str) -> str:
        r = self.responses[min(len(self.calls), len(self.responses) - 1)]
        self.calls.append((system, user))
        return r(system, user) if callable(r) else r


def extract_json(text: str) -> dict:
    """Primo oggetto JSON della risposta (tollera fence ``` e testo attorno)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        start = t.find("{")
        if start < 0:
            raise ValueError("nessun oggetto JSON nella risposta")
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    obj = json.loads(t[start : i + 1])
                    break
        else:
            raise ValueError("JSON non chiuso (risposta troncata?)")
    if not isinstance(obj, dict):
        raise ValueError("la radice del JSON deve essere un oggetto")
    return obj
