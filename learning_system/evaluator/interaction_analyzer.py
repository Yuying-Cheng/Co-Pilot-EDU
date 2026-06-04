"""交互轮数、类型、多样性与连续性分析。"""
from __future__ import annotations
import re
from typing import Any, Dict, Iterable, List
from .constants import INTERACTION_TYPES
from .interaction_classifier import classify_interaction

FOLLOW_UP_MARKERS = ["你刚才", "刚才", "前面", "进一步", "继续", "那么", "那为什么", "基于", "上述", "按照你的", "这个结论", "你的解释"]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def _is_valid_round(round_data: Dict[str, Any], seen_inputs: set[str]) -> bool:
    student_input = _normalize(str(round_data.get("student_input", "")))
    model_output = _normalize(str(round_data.get("model_output", "")))
    if len(student_input) < 4 or len(model_output) < 4:
        return False
    if student_input in seen_inputs:
        return False
    seen_inputs.add(student_input)
    return True


def _mentions_knowledge_point(text: str, previous_output: str, point_names: Iterable[str]) -> bool:
    return any(name and name in text and name in previous_output for name in point_names)


def analyze_interactions(dialogues: List[Dict[str, Any]], knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    type_counts = {kind: 0 for kind in INTERACTION_TYPES}
    seen_inputs: set[str] = set()
    valid_rounds = 0
    follow_up_count = 0
    point_names = [str(point.get("name", "")) for point in knowledge_points]
    previous_model_output = ""
    for dialogue in dialogues:
        student_input = str(dialogue.get("student_input", "")).strip()
        model_output = str(dialogue.get("model_output", "")).strip()
        if _is_valid_round(dialogue, seen_inputs):
            valid_rounds += 1
            for kind in classify_interaction(student_input, previous_model_output):
                type_counts[kind] += 1
            has_marker = any(marker in student_input for marker in FOLLOW_UP_MARKERS)
            has_knowledge_link = _mentions_knowledge_point(student_input, previous_model_output, point_names)
            if previous_model_output and (has_marker or has_knowledge_link):
                follow_up_count += 1
        previous_model_output = model_output
    deep_count = sum(type_counts[kind] for kind in ["表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"])
    follow_up_ratio = round(follow_up_count / max(valid_rounds - 1, 1), 2)
    has_questioning = type_counts["审辨"] > 0
    if has_questioning and deep_count >= 4 and follow_up_ratio >= 0.3:
        depth_level = "较深"
    elif deep_count >= 2 or follow_up_count >= 1:
        depth_level = "一般"
    else:
        depth_level = "较浅"
    return {
        "total_rounds": len(dialogues),
        "valid_rounds": valid_rounds,
        "interaction_types": type_counts,
        "has_follow_up": follow_up_count > 0,
        "has_questioning": has_questioning,
        "depth_level": depth_level,
        "_follow_up_count": follow_up_count,
        "_follow_up_ratio": follow_up_ratio,
        "_deep_count": deep_count,
    }
