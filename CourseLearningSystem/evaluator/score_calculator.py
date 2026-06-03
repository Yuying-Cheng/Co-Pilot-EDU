"""评分计算：严格保持交互质量为核心。"""
from __future__ import annotations
from typing import Any, Dict, List
from .constants import DEFAULT_MIN_ROUNDS, SCORE_LIMITS


def _round_score(valid_rounds: int, min_rounds: int) -> int:
    return 10 if min_rounds <= 0 else min(10, round(10 * valid_rounds / min_rounds))


def _diversity_score(type_counts: Dict[str, int], required_types: List[str]) -> int:
    if required_types:
        hit = sum(1 for kind in required_types if type_counts.get(kind, 0) > 0)
        return round(15 * hit / len(required_types))
    used_count = sum(1 for count in type_counts.values() if count > 0)
    return min(15, used_count * 3)


def calculate_interaction_quality(task: Dict[str, Any], interaction_analysis: Dict[str, Any]) -> int:
    """交互质量50分：轮数10 + 多样性15 + 连续追问10 + 深度/审辨15。"""
    requirements = task.get("interaction_requirements", {})
    min_rounds = int(requirements.get("min_rounds", DEFAULT_MIN_ROUNDS))
    required_types = list(requirements.get("required_types", []))
    type_counts = interaction_analysis["interaction_types"]
    score = _round_score(interaction_analysis["valid_rounds"], min_rounds)
    score += _diversity_score(type_counts, required_types)
    follow_up_ratio = interaction_analysis.get("_follow_up_ratio", 0)
    if follow_up_ratio >= 0.3:
        score += 10
    elif interaction_analysis["has_follow_up"]:
        score += 6
    deep_types_used = sum(1 for kind in ["表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"] if type_counts.get(kind, 0) > 0)
    score += min(8, deep_types_used * 2)
    if interaction_analysis["has_questioning"]:
        score += 7
    return min(SCORE_LIMITS["interaction_quality"], score)


def calculate_knowledge_mastery(knowledge_points: List[Dict[str, Any]], related_ids: List[str], knowledge_analysis: Dict[str, List[str]]) -> int:
    selected = [point for point in knowledge_points if not related_ids or point.get("id") in related_ids]
    if not selected:
        return 0
    weight_map = {"core": 3, "important": 2, "extended": 1}
    total_weight = sum(weight_map.get(str(point.get("importance")), 1) for point in selected)
    covered_ids = set(knowledge_analysis["covered_points"])
    covered_weight = sum(weight_map.get(str(point.get("importance")), 1) for point in selected if point.get("id") in covered_ids)
    return min(25, round(25 * covered_weight / total_weight))


def calculate_presentation(final_report: str, covered_count: int) -> int:
    report = (final_report or "").strip()
    length_score = 8 if len(report) >= 160 else 6 if len(report) >= 80 else 3 if len(report) >= 30 else 0
    structure_markers = ["首先", "其次", "最后", "总结", "比较", "复杂度", "结论"]
    structure_score = min(4, sum(1 for marker in structure_markers if marker in report))
    coverage_score = min(3, covered_count)
    return min(15, length_score + structure_score + coverage_score)


def calculate_reflection(reflection: str) -> int:
    text = (reflection or "").strip()
    length_score = 4 if len(text) >= 80 else 3 if len(text) >= 40 else 1 if text else 0
    markers = ["发现", "一开始", "原来", "不足", "改进", "以后", "质疑", "模型", "仍然", "需要"]
    insight_score = min(6, sum(1 for marker in markers if marker in text))
    return min(10, length_score + insight_score)
