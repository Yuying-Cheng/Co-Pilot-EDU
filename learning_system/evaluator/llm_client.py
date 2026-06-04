# learning_system/evaluator/llm_client.py
# 替换掉原来 CourseLearningSystem 里的 config 导入

from __future__ import annotations
import json, os, re, urllib.error, urllib.request
from typing import Any, Dict


def _get_api_key() -> str:
    """从 learning_system/config.json 读取 API key。"""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "config.json"
    )
    config_path = os.path.normpath(config_path)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("api_key", "")
    return os.getenv("DEEPSEEK_API_KEY", "")


DEFAULT_URL   = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


class LLMClientError(RuntimeError):
    pass


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
    api_key = _get_api_key()
    if not api_key:
        raise LLMClientError("API key not configured")

    payload = {
        "model": DEFAULT_MODEL,
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
        DEFAULT_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMClientError(f"Request failed: {exc}") from exc

    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise LLMClientError("Invalid response format") from exc

    return _extract_json_object(str(content))