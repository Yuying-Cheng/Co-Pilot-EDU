"""Compatibility helpers for presentation clarity analysis."""
from __future__ import annotations

from typing import Any, Dict


def extract_clarity(knowledge_analysis: Dict[str, Any]) -> Dict[str, Any]:
    clarity = knowledge_analysis.get("clarity")
    return clarity if isinstance(clarity, dict) else {}
