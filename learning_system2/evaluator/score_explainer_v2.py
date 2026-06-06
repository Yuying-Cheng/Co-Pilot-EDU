"""Structured score explanations for v2 evaluation output."""
from __future__ import annotations

from typing import Any, Dict, List


INTERACTION_SUBDIMENSION_MAX = {
    "rounds": 10,
    "diversity": 10,
    "continuity": 10,
    "depth": 15,
    "active_thinking": 5,
}


INTERACTION_SUBDIMENSION_NAMES = {
    "rounds": "交互次数与有效性",
    "diversity": "交互方式多样性",
    "continuity": "交互连续性",
    "depth": "交互深度",
    "active_thinking": "主动思考程度",
}


def _level(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score else 0
    if ratio >= 0.8:
        return "较好"
    if ratio >= 0.6:
        return "一般"
    return "较弱"


def _interaction_subreason(key: str, score: int, interaction_analysis: Dict[str, Any]) -> str:
    max_score = INTERACTION_SUBDIMENSION_MAX[key]
    valid_rounds = int(interaction_analysis.get("valid_rounds", 0) or 0)
    total_rounds = int(interaction_analysis.get("total_rounds", 0) or 0)
    type_counts = interaction_analysis.get("interaction_types", {})
    used_types = [kind for kind, count in type_counts.items() if int(count or 0) > 0]
    continuity = interaction_analysis.get("continuity", {}) if isinstance(interaction_analysis.get("continuity"), dict) else {}
    depth = interaction_analysis.get("depth", {}) if isinstance(interaction_analysis.get("depth"), dict) else {}

    if key == "rounds":
        if depth.get("is_answer_scraping"):
            return f"共有{total_rounds}轮对话，其中{valid_rounds}轮被判为有效；但多数轮次偏向连续索要解释，因此该项被压低为{score}/{max_score}。"
        return f"共有{total_rounds}轮对话，其中{valid_rounds}轮被判为有效，按任务轮次要求折算为{score}/{max_score}。"
    if key == "diversity":
        return f"识别到{len(used_types)}类交互方式（{', '.join(used_types) if used_types else '无'}），多样性得分为{score}/{max_score}。"
    if key == "continuity":
        follow_up_count = int(continuity.get("follow_up_count", 0) or 0)
        continuity_level = str(continuity.get("continuity_level", ""))
        return f"共有{follow_up_count}轮被判为承接前文，连续性等级为{continuity_level or '未明确'}，因此得{score}/{max_score}。"
    if key == "depth":
        depth_level = str(depth.get("depth_level", interaction_analysis.get("depth_level", "")))
        signals = []
        if depth.get("has_questioning"):
            signals.append("质疑")
        if depth.get("has_comparison"):
            signals.append("比较分析")
        if depth.get("has_personal_viewpoint"):
            signals.append("个人观点")
        if depth.get("has_hypothesis_testing"):
            signals.append("猜想验证")
        if depth.get("has_error_correction"):
            signals.append("错误修正")
        if depth.get("is_answer_scraping"):
            signals.append("存在要答案式交互倾向")
        return f"深度等级为{depth_level or '未明确'}，主要证据包括{', '.join(signals) if signals else '较少'}，因此得{score}/{max_score}。"
    active_level = str(depth.get("active_thinking_level", ""))
    return f"主动思考等级为{active_level or '未明确'}，结合个人观点、猜想、验证和修正证据，得{score}/{max_score}。"


def build_score_details(
    scores: Dict[str, int],
    interaction_analysis: Dict[str, Any],
    knowledge_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    dimension_scores = interaction_analysis.get("dimension_scores", {})
    interaction_subdimensions = {}
    raw_interaction_sum = 0
    for key, max_score in INTERACTION_SUBDIMENSION_MAX.items():
        score = int(dimension_scores.get(key, 0) or 0)
        raw_interaction_sum += score
        interaction_subdimensions[key] = {
            "name": INTERACTION_SUBDIMENSION_NAMES[key],
            "score": score,
            "max_score": max_score,
            "level": _level(score, max_score),
            "reason": _interaction_subreason(key, score, interaction_analysis),
        }

    adjustments: List[Dict[str, Any]] = []
    interaction_score = int(scores.get("interaction_quality", 0) or 0)
    if raw_interaction_sum != interaction_score:
        adjustments.append(
            {
                "type": "cap",
                "before": raw_interaction_sum,
                "after": interaction_score,
                "reason": "检测到多数轮次以连续询问和获取解释为主，缺少充分的验证、修正和创造性推进，因此对交互质量设置上限。",
            }
        )

    knowledge_items = knowledge_analysis.get("knowledge_points", [])
    fully = [item for item in knowledge_items if isinstance(item, dict) and item.get("coverage") == "充分覆盖"]
    partial = [item for item in knowledge_items if isinstance(item, dict) and item.get("coverage") == "部分覆盖"]
    missing = [item for item in knowledge_items if isinstance(item, dict) and item.get("coverage") == "未覆盖"]
    weak_points = [str(item) for item in knowledge_analysis.get("weak_points", []) if item]
    clarity = knowledge_analysis.get("clarity", {}) if isinstance(knowledge_analysis.get("clarity"), dict) else {}
    reflection = knowledge_analysis.get("reflection", {}) if isinstance(knowledge_analysis.get("reflection"), dict) else {}

    return {
        "total": {
            "score": sum(int(value or 0) for value in scores.values()),
            "max_score": 100,
            "reason": "总分由交互质量、知识掌握、成果呈现、学习反思四个维度相加得到。",
        },
        "dimensions": {
            "interaction_quality": {
                "name": "交互质量",
                "score": interaction_score,
                "max_score": 50,
                "level": _level(interaction_score, 50),
                "reason": "交互质量由交互次数与有效性、交互方式多样性、交互连续性、交互深度、主动思考程度五个小项综合计算。",
                "subdimensions": interaction_subdimensions,
                "adjustments": adjustments,
            },
            "knowledge_mastery": {
                "name": "知识掌握",
                "score": int(scores.get("knowledge_mastery", 0) or 0),
                "max_score": 25,
                "level": _level(int(scores.get("knowledge_mastery", 0) or 0), 25),
                "reason": f"任务关联知识点中，充分覆盖{len(fully)}个，部分覆盖{len(partial)}个，未覆盖{len(missing)}个；薄弱点包括{', '.join(weak_points) if weak_points else '无明显薄弱点'}。",
            },
            "presentation": {
                "name": "成果呈现",
                "score": int(scores.get("presentation", 0) or 0),
                "max_score": 15,
                "level": _level(int(scores.get("presentation", 0) or 0), 15),
                "reason": f"报告结构评价为{clarity.get('structure', '未明确')}；主要问题为{'; '.join(map(str, clarity.get('problems', []))) if clarity.get('problems') else '未发现明显表达问题'}。",
            },
            "reflection": {
                "name": "学习反思",
                "score": int(scores.get("reflection", 0) or 0),
                "max_score": 10,
                "level": _level(int(scores.get("reflection", 0) or 0), 10),
                "reason": f"反思质量等级为{reflection.get('level', '未明确')}；主要问题为{'; '.join(map(str, reflection.get('problems', []))) if reflection.get('problems') else '反思内容具备一定质量'}。",
            },
        },
        "rubric": {
            "interaction_quality": "50分：交互次数与有效性10分、交互方式多样性10分、交互连续性10分、交互深度15分、主动思考程度5分。",
            "knowledge_mastery": "25分：按任务关联知识点覆盖情况计算，充分覆盖按100%权重，部分覆盖按50%权重，未覆盖按0计算。",
            "presentation": "15分：评价最终报告是否围绕任务、结构是否清晰、概念是否准确、是否有比较推导或总结。",
            "reflection": "10分：评价学习反思是否体现认知变化、不足发现、质疑意识和后续改进。",
        },
    }
