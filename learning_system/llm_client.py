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


def call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> dict:
    system_with_json = system_prompt + "\n\n重要：你的回复必须是纯JSON格式，不包含任何markdown代码块或多余文字。"
    text = call_llm(system_with_json, user_prompt, max_tokens)
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    return json.loads(text.strip())
