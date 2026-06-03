import os
import json
from pathlib import Path

# 全系统通用配置。优先读取环境变量，避免把真实 API Key 写进源码。
_LOCAL_CONFIG = Path(__file__).with_name("config.local.json")
_local = {}
if _LOCAL_CONFIG.exists():
    try:
        _local = json.loads(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        _local = {}

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or _local.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or _local.get("BASE_URL", "https://api.deepseek.com")
