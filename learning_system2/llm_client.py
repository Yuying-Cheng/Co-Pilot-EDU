"""
LLM client — DeepSeek (OpenAI-compatible) + config.json
"""

import json
import re
import os
from openai import OpenAI

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_api_key() -> str:
    return load_config().get("api_key", "")

def is_configured() -> bool:
    return bool(get_api_key())


# ── LLM calls ─────────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    key = get_api_key()
    if not key:
        raise RuntimeError("未配置 API Key，请先在设置页填写。")
    return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content


def _strip_json_fence(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _extract_json_object(text: str) -> str:
    text = _strip_json_fence(text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _repair_json_text(bad_json: str, error_msg: str, max_tokens: int) -> dict:
    repair_system = (
        "你是一个 JSON 修复器。"
        "用户会提供一段本应为 JSON 的文本和解析错误信息。"
        "你的任务是只输出一个修复后的合法 JSON 对象，不要输出解释。"
    )
    repair_prompt = f"""请修复下面的 JSON，使其能被标准 JSON 解析。

解析错误：
{error_msg}

原始文本：
{bad_json}
"""
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": repair_system},
                {"role": "user", "content": repair_prompt},
            ],
        )
        fixed = resp.choices[0].message.content
    except Exception:
        fixed = call_llm(repair_system, repair_prompt, max_tokens=max_tokens)
    return json.loads(_extract_json_object(fixed))


def call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> dict:
    system_with_json = system_prompt + "\n\n重要：你的回复必须是纯JSON格式，不包含任何markdown代码块或多余文字。"
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_with_json},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = _extract_json_object(resp.choices[0].message.content)
    except Exception:
        text = _extract_json_object(call_llm(system_with_json, user_prompt, max_tokens))
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return _repair_json_text(text, str(exc), max_tokens=max_tokens)
