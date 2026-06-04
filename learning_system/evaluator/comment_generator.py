"""根据分析结果生成可读评语。"""
from __future__ import annotations
from typing import Any, Dict


def generate_comment(interaction_score: int, interaction_analysis: Dict[str, Any], knowledge_analysis: Dict[str, Any]) -> str:
    type_counts = interaction_analysis["interaction_types"]
    used_types = [kind for kind, count in type_counts.items() if count > 0]
    positives, suggestions = [], []
    if interaction_analysis["valid_rounds"] >= 10:
        positives.append("完成了不少于10轮的有效交互")
    else:
        suggestions.append("补足有效交互轮次，避免仅以零散问题完成任务")
    if interaction_analysis["has_follow_up"]:
        positives.append("能够结合前一轮回答继续追问")
    else:
        suggestions.append("在模型回答后继续追问原因、条件或反例，形成连续探究链")
    if type_counts.get("审辨", 0) > 0:
        positives.append("存在质疑或审辨行为")
    else:
        suggestions.append("增加对模型结论的质疑、验证或反例分析")
    if len(used_types) < 4:
        suggestions.append("增加表达见解、猜想、想象或创新等交互形式")
    if knowledge_analysis["weak_points"]:
        suggestions.append("加强对" + "、".join(knowledge_analysis["weak_points"]) + "的讨论")
    first = "该学生" + "，".join(positives) + "。" if positives else "该学生的交互目前以浅层询问为主。"
    quality = "整体交互过程体现出较好的主动学习意识。" if interaction_score >= 40 else "交互过程具备一定探究性，但深度仍有提升空间。" if interaction_score >= 25 else "交互过程较为单一，尚未充分体现探究式学习特点。"
    advice = "建议后续" + "；".join(suggestions) + "。" if suggestions else "建议继续保持当前探究方式，并进一步总结学习收获。"
    return first + quality + advice
