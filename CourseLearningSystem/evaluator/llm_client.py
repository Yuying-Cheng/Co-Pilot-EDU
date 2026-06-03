"""Minimal DeepSeek client used by the second-week semantic evaluator."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict
from config import DEEPSEEK_API_KEY, BASE_URL


DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


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


def call_llm(prompt: str, *, timeout: int = 60) -> Dict[str, Any]:
    """Call DeepSeek and parse the assistant response as JSON.

    Environment variables:
    - DEEPSEEK_API_KEY: required API key.
    - DEEPSEEK_API_URL: optional OpenAI-compatible endpoint.
    - DEEPSEEK_MODEL: optional model name, defaults to deepseek-chat.
    The same keys can also be placed in a project-local .env.local file.
    """
    if not DEEPSEEK_API_KEY:
        raise LLMClientError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": DEFAULT_DEEPSEEK_MODEL,
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

    api_url = f"{BASE_URL.rstrip('/')}/chat/completions" if BASE_URL else DEFAULT_DEEPSEEK_URL

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
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
