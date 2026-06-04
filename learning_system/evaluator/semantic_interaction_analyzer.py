"""Second-week semantic interaction analysis with a rule fallback."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .interaction_analyzer import analyze_interactions
from .llm_client import LLMClientError, call_llm
from .prompts import INTERACTION_TYPES_V2, build_interaction_prompt


TYPE_PATTERNS = {
    "询问": [r"[?？]", r"什么|为什么|如何|怎样|怎么|请解释|能否|是否|区别"],
    "表达见解": [r"我认为|我觉得|我的理解|在我看来|也就是说|可以理解为|我总结"],
    "审辨": [r"不一定|不认同|有问题|不准确|反例|质疑|验证|是否真的|并不等于|限定条件"],
    "猜想": [r"我猜|猜想|假设|会不会|可能|如果.+那么|我推测"],
    "想象": [r"想象|类比|比作|好像|场景|类似"],
    "创新": [r"改进|优化方案|重新设计|新方法|变体|推广|能不能改成|我设计"],
}


def _clean_types(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [item for item in values if item in INTERACTION_TYPES_V2]


def _rule_classify(student_input: str, previous_output: str) -> List[str]:
    text = student_input or ""
    types: List[str] = []
    for kind, patterns in TYPE_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            types.append(kind)
    mentor_question = bool(re.search(r"你认为|思考|试着|如果|为什么|你能否|你会如何", previous_output or ""))
    student_reasoning = bool(re.search(r"我认为|因为|所以|因此|应该|首先|这说明", text))
    if mentor_question and student_reasoning:
        types.append("苏格拉底回答")
    if not types and len(text.strip()) >= 4:
        types.append("询问")
    return [kind for kind in INTERACTION_TYPES_V2 if kind in set(types)]


def _is_effective(student_input: str, model_output: str, seen_inputs: set[str]) -> bool:
    normalized = re.sub(r"\s+", "", student_input or "")
    output = re.sub(r"\s+", "", model_output or "")
    if len(normalized) < 4 or len(output) < 4:
        return False
    if normalized in seen_inputs:
        return False
    normalized_plain = re.sub(r"[。！？?，,、；;：:\s]+", "", normalized)
    if normalized_plain in {"继续", "继续解释", "再说", "好的", "明白", "完成", "没有了"}:
        return False
    seen_inputs.add(normalized)
    return True


def _fallback_semantic_analysis(dialogues: List[Dict[str, Any]], knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    rule_internal = analyze_interactions(dialogues, knowledge_points)
    seen_inputs: set[str] = set()
    rounds: List[Dict[str, Any]] = []
    type_counts = {kind: 0 for kind in INTERACTION_TYPES_V2}
    follow_up_count = 0
    evidence: List[Dict[str, Any]] = []
    previous_output = ""
    follow_markers = ["你刚才", "刚才", "前面", "进一步", "继续", "那么", "那为什么", "基于", "上述", "按照你的", "这个结论", "你的解释"]
    for index, dialogue in enumerate(dialogues, start=1):
        round_no = int(dialogue.get("round", index) or index)
        student_input = str(dialogue.get("student_input", ""))
        model_output = str(dialogue.get("model_output", ""))
        is_effective = _is_effective(student_input, model_output, seen_inputs)
        types = _rule_classify(student_input, previous_output) if is_effective else []
        for kind in types:
            type_counts[kind] += 1
        is_follow_up = is_effective and bool(previous_output) and any(marker in student_input for marker in follow_markers)
        if is_follow_up:
            follow_up_count += 1
        reason = "规则兜底识别：" + ("、".join(types) if types else "无有效交互类型")
        rounds.append(
            {
                "round": round_no,
                "interaction_types": types,
                "reason": reason,
                "is_effective": is_effective,
                "is_follow_up": is_follow_up,
                "follow_up_target": "上一轮模型回答" if is_follow_up else "",
                "continuity_level": "中" if is_follow_up else "无",
            }
        )
        if types and len(evidence) < 6:
            evidence.append({"round": round_no, "type": types[0], "reason": reason})
        previous_output = model_output

    valid_rounds = sum(1 for item in rounds if item["is_effective"])
    follow_ratio = follow_up_count / max(valid_rounds - 1, 1)
    deep_flags = {
        "has_questioning": type_counts["审辨"] > 0 or bool(rule_internal.get("has_questioning")),
        "has_error_correction": any("错误" in str(item.get("reason", "")) for item in rounds),
        "has_comparison": any("比较" in str(d.get("student_input", "")) or "区别" in str(d.get("student_input", "")) for d in dialogues),
        "has_personal_viewpoint": type_counts["表达见解"] > 0,
        "has_hypothesis_testing": type_counts["猜想"] > 0,
    }
    deep_signal_count = sum(1 for value in deep_flags.values() if value)
    depth_level = "较深" if deep_signal_count >= 4 and follow_ratio >= 0.3 else "一般" if deep_signal_count >= 2 or follow_ratio >= 0.2 else "较浅"
    return {
        "llm_used": False,
        "fallback_reason": "未启用大模型或大模型调用失败，已使用规则兜底分析",
        "total_rounds": len(dialogues),
        "valid_rounds": valid_rounds,
        "interaction_types": type_counts,
        "rounds": rounds,
        "has_follow_up": follow_up_count > 0,
        "has_questioning": deep_flags["has_questioning"],
        "depth_level": depth_level,
        "continuity": {
            "follow_up_count": follow_up_count,
            "continuity_level": "强" if follow_ratio >= 0.6 else "中" if follow_ratio >= 0.3 else "弱",
            "has_inquiry_chain": follow_ratio >= 0.3 and valid_rounds >= 6,
            "reason": "规则兜底基于衔接词和轮次统计判断连续性",
        },
        "depth": {
            **deep_flags,
            "is_answer_scraping": valid_rounds >= 8 and len([k for k, v in type_counts.items() if v > 0]) <= 2 and follow_ratio < 0.3,
            "active_thinking_level": "强" if deep_signal_count >= 4 else "中" if deep_signal_count >= 2 else "弱",
            "depth_level": depth_level,
            "depth_reason": "规则兜底基于表达见解、审辨、猜想、比较和追问等信号判断深度",
        },
        "evidence": evidence,
        "problems": [],
    }


def _normalize_llm_analysis(data: Dict[str, Any], dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
    rounds = data.get("rounds", [])
    if not isinstance(rounds, list):
        rounds = []
    normalized_rounds: List[Dict[str, Any]] = []
    type_counts = {kind: 0 for kind in INTERACTION_TYPES_V2}
    follow_up_count = 0
    valid_rounds = 0
    for index, dialogue in enumerate(dialogues, start=1):
        raw = rounds[index - 1] if index - 1 < len(rounds) and isinstance(rounds[index - 1], dict) else {}
        types = _clean_types(raw.get("interaction_types"))
        is_effective = bool(raw.get("is_effective", True))
        is_follow_up = bool(raw.get("is_follow_up", False)) if index > 1 else False
        if is_effective:
            valid_rounds += 1
            for kind in types:
                type_counts[kind] += 1
        if is_follow_up:
            follow_up_count += 1
        normalized_rounds.append(
            {
                "round": int(raw.get("round", dialogue.get("round", index)) or index),
                "interaction_types": types,
                "reason": str(raw.get("reason", "")),
                "is_effective": is_effective,
                "is_follow_up": is_follow_up,
                "follow_up_target": str(raw.get("follow_up_target", "")),
                "continuity_level": str(raw.get("continuity_level", "无")),
            }
        )
    student_inputs = [str(dialogue.get("student_input", "")) for dialogue in dialogues]
    question_rounds = sum(1 for text in student_inputs if "?" in text or "？" in text or "是否" in text or "什么" in text)
    personal_marker_count = sum(1 for text in student_inputs if re.search(r"我认为|我觉得|我的理解|在我看来|我猜|我推测|我设计|我质疑|我不认同", text))
    deterministic_answer_scraping = valid_rounds >= 8 and question_rounds / max(valid_rounds, 1) >= 0.8 and personal_marker_count == 0
    continuity = data.get("continuity") if isinstance(data.get("continuity"), dict) else {}
    depth = data.get("depth") if isinstance(data.get("depth"), dict) else {}
    if deterministic_answer_scraping:
        depth["is_answer_scraping"] = True
        depth["active_thinking_level"] = "弱"
        if depth.get("depth_level") == "较深":
            depth["depth_level"] = "一般"
    evidence = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    return {
        "llm_used": True,
        "total_rounds": len(dialogues),
        "valid_rounds": valid_rounds,
        "interaction_types": type_counts,
        "rounds": normalized_rounds,
        "has_follow_up": follow_up_count > 0 or bool(continuity.get("has_inquiry_chain")),
        "has_questioning": bool(depth.get("has_questioning")) or type_counts["审辨"] > 0,
        "depth_level": str(depth.get("depth_level", "一般")),
        "continuity": {
            "follow_up_count": int(continuity.get("follow_up_count", follow_up_count) or follow_up_count),
            "continuity_level": str(continuity.get("continuity_level", "中")),
            "has_inquiry_chain": bool(continuity.get("has_inquiry_chain", False)),
            "reason": str(continuity.get("reason", "")),
        },
        "depth": depth,
        "evidence": evidence[:8],
        "problems": data.get("problems", []) if isinstance(data.get("problems"), list) else [],
    }


def analyze_interactions_semantic(
    task: Dict[str, Any],
    submission: Dict[str, Any],
    knowledge_points: List[Dict[str, Any]],
    *,
    use_llm: bool = True,
) -> Dict[str, Any]:
    dialogues = list(submission.get("dialogues", []))
    if not use_llm:
        return _fallback_semantic_analysis(dialogues, knowledge_points)
    try:
        data = call_llm(build_interaction_prompt(task, dialogues))
        return _normalize_llm_analysis(data, dialogues)
    except (LLMClientError, ValueError, TypeError, KeyError) as exc:
        fallback = _fallback_semantic_analysis(dialogues, knowledge_points)
        fallback["fallback_reason"] = str(exc)
        return fallback
