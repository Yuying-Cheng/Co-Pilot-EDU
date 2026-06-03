"""Readable comments and improvement suggestions for v2 evaluation."""
from __future__ import annotations

from typing import Any, Dict, List


def _score_level(score: int, full_score: int) -> str:
    ratio = score / full_score if full_score else 0
    if ratio >= 0.8:
        return "较好"
    if ratio >= 0.6:
        return "一般"
    return "较弱"


def generate_feedback_v2(
    interaction_score: int,
    knowledge_score: int,
    presentation_score: int,
    reflection_score: int,
    interaction_analysis: Dict[str, Any],
    knowledge_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Return separated teacher-facing comment and actionable suggestions."""
    dimension_scores = interaction_analysis.get("dimension_scores", {})
    depth = interaction_analysis.get("depth", {}) if isinstance(interaction_analysis.get("depth"), dict) else {}
    weak_points = [str(item) for item in knowledge_analysis.get("weak_points", []) if item]

    highlights: List[str] = []
    if int(interaction_analysis.get("valid_rounds", 0) or 0) >= 8:
        highlights.append("有效交互轮次较充分")
    if dimension_scores.get("continuity", 0) >= 8:
        highlights.append("能够围绕前文回答继续推进问题")
    if interaction_analysis.get("has_questioning"):
        highlights.append("体现了一定的质疑和审辨意识")
    if knowledge_score >= 18:
        highlights.append("任务关联知识点覆盖较完整")
    elif knowledge_score >= 10:
        highlights.append("对部分任务知识点已有基本涉及")
    if presentation_score >= 10:
        highlights.append("成果报告表达较清晰")
    if reflection_score >= 7:
        highlights.append("学习反思能体现一定的认知变化")

    if highlights:
        readable_comment = "该学生" + "，".join(highlights) + "。"
    else:
        readable_comment = "该学生目前主要停留在基础提问和答案获取层面，主动建构知识的证据还不充分。"

    readable_comment += (
        f"交互质量为{interaction_score}/50，处于{_score_level(interaction_score, 50)}水平；"
        f"知识掌握为{knowledge_score}/25，处于{_score_level(knowledge_score, 25)}水平；"
        f"成果呈现为{presentation_score}/15，处于{_score_level(presentation_score, 15)}水平；"
        f"学习反思为{reflection_score}/10，处于{_score_level(reflection_score, 10)}水平。"
    )

    suggestions: List[str] = []
    if dimension_scores.get("rounds", 0) < 8:
        if depth.get("is_answer_scraping"):
            suggestions.append("虽然交互轮次基本达标，但多数轮次仍以连续询问为主，建议增加个人判断、验证和反思性追问。")
        else:
            suggestions.append("补足有效交互轮次，避免使用“继续解释”等简单重复内容刷轮数。")
    if dimension_scores.get("diversity", 0) < 6:
        suggestions.append("增加表达见解、审辨、猜想、比较分析等交互方式，不要只连续询问概念。")
    if dimension_scores.get("continuity", 0) < 7:
        suggestions.append("每一轮提问应明确承接上一轮模型回答，围绕同一问题逐步深入。")
    if dimension_scores.get("depth", 0) < 10:
        suggestions.append("加强对模型结论的条件分析、反例验证和不同方案比较，体现更深层的思辨过程。")
    if dimension_scores.get("active_thinking", 0) < 3:
        suggestions.append("更多写出自己的判断、猜想和修正过程，而不是只等待模型给出答案。")
    if weak_points:
        suggestions.append("加强对" + "、".join(weak_points[:4]) + "等薄弱知识点的展开。")
    if presentation_score < 9:
        suggestions.append("最终报告需要更清晰地围绕任务组织结构，补充比较、推导或总结。")
    if reflection_score == 0:
        suggestions.append("补充学习反思，说明自己的认知变化、仍存在的不足和后续改进方向。")
    elif reflection_score < 6:
        suggestions.append("学习反思可以进一步具体化，写清楚哪些观点发生了变化以及为什么。")
    if not suggestions:
        suggestions.append("继续保持当前探究方式，并进一步沉淀个人理解和迁移应用。")

    return {
        "readable_comment": readable_comment,
        "improvement_suggestions": suggestions,
        "comment": readable_comment + "改进建议：" + "".join(suggestions),
    }


def generate_comment_v2(
    interaction_score: int,
    interaction_analysis: Dict[str, Any],
    knowledge_analysis: Dict[str, Any],
    presentation_score: int,
    reflection_score: int,
    knowledge_score: int = 0,
) -> str:
    """Backward-compatible helper returning a single text comment."""
    return generate_feedback_v2(
        interaction_score,
        knowledge_score,
        presentation_score,
        reflection_score,
        interaction_analysis,
        knowledge_analysis,
    )["comment"]
