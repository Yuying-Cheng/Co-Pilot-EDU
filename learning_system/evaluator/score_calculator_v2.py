"""Fixed scoring rubric for the second-week semantic evaluator."""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import DEFAULT_MIN_ROUNDS
from .prompts import INTERACTION_TYPES_V2


def _clamp(value: int, upper: int) -> int:
    return max(0, min(upper, int(value)))


def calculate_interaction_quality_v2(task: Dict[str, Any], analysis: Dict[str, Any]) -> tuple[int, Dict[str, int]]:
    requirements = task.get("interaction_requirements", {})
    min_rounds = int(requirements.get("min_rounds", DEFAULT_MIN_ROUNDS) or DEFAULT_MIN_ROUNDS)
    valid_rounds = int(analysis.get("valid_rounds", 0) or 0)
    type_counts = analysis.get("interaction_types", {})
    depth = analysis.get("depth", {}) if isinstance(analysis.get("depth"), dict) else {}
    continuity = analysis.get("continuity", {}) if isinstance(analysis.get("continuity"), dict) else {}

    rounds_score = 10 if min_rounds <= 0 else round(10 * min(valid_rounds, min_rounds) / min_rounds)
    if depth.get("is_answer_scraping"):
        rounds_score = min(rounds_score, 6)

    required_types = list(requirements.get("required_types", []) or [])
    if required_types:
        hit = sum(1 for kind in required_types if int(type_counts.get(kind, 0) or 0) > 0)
        diversity_score = round(10 * hit / len(required_types))
    else:
        used = sum(1 for kind in INTERACTION_TYPES_V2 if int(type_counts.get(kind, 0) or 0) > 0)
        diversity_score = min(10, used * 2)

    follow_up_count = int(continuity.get("follow_up_count", 0) or 0)
    follow_ratio = follow_up_count / max(valid_rounds - 1, 1)
    level = str(continuity.get("continuity_level", ""))
    if level == "强" or follow_ratio >= 0.6:
        continuity_score = 10
    elif level in {"中", "较强"} or follow_ratio >= 0.35:
        continuity_score = 8
    elif follow_ratio >= 0.15 or analysis.get("has_follow_up"):
        continuity_score = 5
    elif follow_up_count > 0:
        continuity_score = 3
    else:
        continuity_score = 1 if valid_rounds >= 2 else 0
    if continuity.get("has_inquiry_chain"):
        continuity_score = min(10, continuity_score + 1)

    depth_level = str(depth.get("depth_level", analysis.get("depth_level", "")))
    depth_signals = sum(
        1
        for key in ["has_questioning", "has_error_correction", "has_comparison", "has_personal_viewpoint", "has_hypothesis_testing"]
        if depth.get(key)
    )
    if depth_level == "较深":
        depth_score = 12 + min(3, depth_signals)
    elif depth_level == "一般":
        depth_score = 7 + min(4, depth_signals)
    else:
        depth_score = 2 + min(4, depth_signals)
    if depth.get("is_answer_scraping"):
        depth_score = min(depth_score, 6)

    active_level = str(depth.get("active_thinking_level", ""))
    if active_level == "强" or depth_signals >= 4:
        active_score = 5
    elif active_level == "中" or depth_signals >= 2:
        active_score = 3
    elif depth.get("has_personal_viewpoint"):
        active_score = 2
    else:
        active_score = 0

    dimension_scores = {
        "rounds": _clamp(rounds_score, 10),
        "diversity": _clamp(diversity_score, 10),
        "continuity": _clamp(continuity_score, 10),
        "depth": _clamp(depth_score, 15),
        "active_thinking": _clamp(active_score, 5),
    }
    total = sum(dimension_scores.values())
    if depth.get("is_answer_scraping"):
        total = min(total, 28)
    return total, dimension_scores


def calculate_knowledge_mastery_v2(knowledge_points: List[Dict[str, Any]], related_ids: List[str], analysis: Dict[str, Any]) -> int:
    selected = [point for point in knowledge_points if not related_ids or str(point.get("id")) in set(map(str, related_ids))]
    if not selected:
        return 0
    coverage_by_id = {
        str(item.get("id")): str(item.get("coverage", "未覆盖"))
        for item in analysis.get("knowledge_points", [])
        if isinstance(item, dict)
    }
    weight_map = {"core": 3, "important": 2, "extended": 1}
    total_weight = sum(weight_map.get(str(point.get("importance")), 1) for point in selected)
    earned = 0.0
    for point in selected:
        coverage = coverage_by_id.get(str(point.get("id")), "未覆盖")
        multiplier = 1.0 if coverage == "充分覆盖" else 0.5 if coverage == "部分覆盖" else 0.0
        earned += weight_map.get(str(point.get("importance")), 1) * multiplier
    return _clamp(round(25 * earned / total_weight), 25)


def calculate_presentation_v2(knowledge_analysis: Dict[str, Any]) -> int:
    clarity = knowledge_analysis.get("clarity", {}) if isinstance(knowledge_analysis.get("clarity"), dict) else {}
    return _clamp(int(clarity.get("clarity_score", 0) or 0), 15)


def calculate_reflection_v2(knowledge_analysis: Dict[str, Any]) -> int:
    reflection = knowledge_analysis.get("reflection", {}) if isinstance(knowledge_analysis.get("reflection"), dict) else {}
    return _clamp(int(reflection.get("reflection_score", 0) or 0), 10)
