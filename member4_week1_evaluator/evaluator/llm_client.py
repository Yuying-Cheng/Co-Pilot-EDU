"""Minimal DeepSeek client used by the second-week semantic evaluator."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
LOCAL_ENV_FILE = Path(__file__).resolve().parents[1] / ".env.local"


class LLMClientError(RuntimeError):
    """Raised when the semantic model cannot return a usable JSON object."""


def _extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise LLMClientError("LLM response does not contain a JSON object")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise LLMClientError("LLM response JSON root must be an object")
    return data


def _load_local_env() -> Dict[str, str]:
    if not LOCAL_ENV_FILE.exists():
        return {}
    values: Dict[str, str] = {}
    for line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_config(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or _load_local_env().get(name) or default


def call_llm(prompt: str, *, timeout: int = 60) -> Dict[str, Any]:
    """Call DeepSeek and parse the assistant response as JSON.

    Environment variables:
    - DEEPSEEK_API_KEY: required API key.
    - DEEPSEEK_API_URL: optional OpenAI-compatible endpoint.
    - DEEPSEEK_MODEL: optional model name, defaults to deepseek-chat.
    The same keys can also be placed in a project-local .env.local file.
    """
    api_key = _get_config("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMClientError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": _get_config("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        "messages": [
            {
                "role": "system",
                "content": "你是教学评价系统中的语义特征识别器。只输出合法 JSON，不要输出 Markdown。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        _get_config("DEEPSEEK_API_URL", DEFAULT_DEEPSEEK_URL),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMClientError(f"DeepSeek request failed: {exc}") from exc

    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMClientError("DeepSeek response format is invalid") from exc
    return _extract_json_object(str(content))
