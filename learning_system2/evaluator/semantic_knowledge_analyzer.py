"""Semantic knowledge, presentation, and reflection analysis."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .llm_client import LLMClientError, call_llm
from .prompts import build_knowledge_prompt


COVERAGE_VALUES = {"充分覆盖", "部分覆盖", "未覆盖"}


OUTPUT_KEYWORDS = [
    "报告", "思维导图", "比对", "遗漏", "补全", "推导", "递推式", "复杂度",
    "空间复杂度", "时间复杂度", "判断题", "解析", "流程", "关键思考", "总结",
]


def _select_related_points(knowledge_points: List[Dict[str, Any]], related_ids: List[str]) -> List[Dict[str, Any]]:
    return [point for point in knowledge_points if not related_ids or str(point.get("id")) in set(map(str, related_ids))]


def _fallback_knowledge_analysis(
    task: Dict[str, Any],
    submission: Dict[str, Any],
    knowledge_points: List[Dict[str, Any]],
    related_ids: List[str],
) -> Dict[str, Any]:
    selected = _select_related_points(knowledge_points, related_ids)
    text_parts = [str(item.get("student_input", "")) for item in submission.get("dialogues", [])]
    text_parts.extend([str(submission.get("final_report", "")), str(submission.get("reflection", ""))])
    combined_text = "\n".join(text_parts)
    items: List[Dict[str, Any]] = []
    missing_points: List[str] = []
    weak_points: List[str] = []
    for point in selected:
        point_id = str(point.get("id", ""))
        name = str(point.get("name", ""))
        aliases = [name] + [str(value) for value in point.get("aliases", [])] + [str(value) for value in point.get("keywords", [])]
        hit_count = sum(1 for alias in aliases if alias and alias in combined_text)
        if hit_count >= 2 or (name and name in combined_text):
            coverage = "充分覆盖"
        elif hit_count == 1:
            coverage = "部分覆盖"
        else:
            coverage = "未覆盖"
        if coverage == "未覆盖":
            missing_points.append(point_id)
            if point.get("importance") in {"core", "important"}:
                weak_points.append(name)
        elif coverage == "部分覆盖" and point.get("importance") in {"core", "important"}:
            weak_points.append(name)
        items.append({"id": point_id, "name": name, "coverage": coverage, "evidence": "规则兜底基于知识点名称/别名命中判断"})

    report = str(submission.get("final_report", "")).strip()
    reflection = str(submission.get("reflection", "")).strip()
    structure_markers = ["首先", "其次", "最后", "总结", "比较", "复杂度", "结论", "因此"]
    clarity_score = min(15, (7 if len(report) >= 160 else 5 if len(report) >= 80 else 2 if report else 0) + sum(1 for marker in structure_markers if marker in report))
    reflection_score = min(10, (4 if len(reflection) >= 80 else 3 if len(reflection) >= 40 else 1 if reflection else 0) + sum(1 for marker in ["发现", "不足", "改进", "以后", "质疑", "反思"] if marker in reflection))
    specific_output = str(task.get("output_requirements", {}).get("specific_output", ""))
    required_outputs = [str(item) for item in task.get("output_requirements", {}).get("required_outputs", [])]
    missing_outputs: List[str] = []
    if not report:
        missing_outputs.append("未提交最终成果报告")
    for keyword in OUTPUT_KEYWORDS:
        if keyword in specific_output and keyword not in report:
            missing_outputs.append(keyword)
    for item in required_outputs:
        if item and item not in report and item not in {"交互记录"}:
            missing_outputs.append(item)
    missing_outputs = list(dict.fromkeys(missing_outputs))
    return {
        "llm_used": False,
        "fallback_reason": "未启用大模型或大模型调用失败，已使用规则兜底分析",
        "knowledge_points": items,
        "covered_points": [item["id"] for item in items if item["coverage"] == "充分覆盖"],
        "partial_points": [item["id"] for item in items if item["coverage"] == "部分覆盖"],
        "missing_points": missing_points,
        "weak_points": weak_points,
        "clarity": {
            "clarity_score": clarity_score,
            "structure": "较清晰" if clarity_score >= 11 else "一般" if clarity_score >= 7 else "较弱",
            "strengths": ["报告具备一定内容基础"] if report else [],
            "problems": [] if report else ["未提交最终报告"],
            "is_answer_pileup": False,
            "is_missing_report": not bool(report),
        },
        "output_compliance": {
            "matches_task": bool(report) and not missing_outputs,
            "matched_outputs": [],
            "missing_outputs": missing_outputs,
            "reason": "规则兜底基于任务成果关键词与最终报告文本匹配判断",
        },
        "reflection": {
            "reflection_score": reflection_score,
            "level": "较好" if reflection_score >= 8 else "一般" if reflection_score >= 4 else "缺失或较弱",
            "strengths": ["有学习反思"] if reflection else [],
            "problems": [] if reflection else ["未提交学习反思"],
        },
    }


def _normalize_knowledge_analysis(data: Dict[str, Any], selected_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    raw_items = data.get("knowledge_points", [])
    raw_by_id = {str(item.get("id")): item for item in raw_items if isinstance(item, dict)}
    items: List[Dict[str, Any]] = []
    covered: List[str] = []
    partial: List[str] = []
    missing: List[str] = []
    weak: List[str] = []
    for point in selected_points:
        point_id = str(point.get("id", ""))
        raw = raw_by_id.get(point_id, {})
        coverage = str(raw.get("coverage", "未覆盖"))
        if coverage not in COVERAGE_VALUES:
            coverage = "未覆盖"
        name = str(raw.get("name", point.get("name", "")))
        item = {
            "id": point_id,
            "name": name,
            "coverage": coverage,
            "evidence": str(raw.get("evidence", "")),
        }
        items.append(item)
        if coverage == "充分覆盖":
            covered.append(point_id)
        elif coverage == "部分覆盖":
            partial.append(point_id)
            if point.get("importance") in {"core", "important"}:
                weak.append(name)
        else:
            missing.append(point_id)
            if point.get("importance") in {"core", "important"}:
                weak.append(name)
    clarity = data.get("clarity") if isinstance(data.get("clarity"), dict) else {}
    output_compliance = data.get("output_compliance") if isinstance(data.get("output_compliance"), dict) else {}
    reflection = data.get("reflection") if isinstance(data.get("reflection"), dict) else {}
    return {
        "llm_used": True,
        "knowledge_points": items,
        "covered_points": covered,
        "partial_points": partial,
        "missing_points": missing,
        "weak_points": list(dict.fromkeys([str(item) for item in data.get("weak_points", weak) if item] or weak)),
        "clarity": {
            "clarity_score": max(0, min(15, int(clarity.get("clarity_score", 0) or 0))),
            "structure": str(clarity.get("structure", "")),
            "strengths": clarity.get("strengths", []) if isinstance(clarity.get("strengths"), list) else [],
            "problems": clarity.get("problems", []) if isinstance(clarity.get("problems"), list) else [],
            "is_answer_pileup": bool(clarity.get("is_answer_pileup", False)),
            "is_missing_report": bool(clarity.get("is_missing_report", False)),
        },
        "output_compliance": {
            "matches_task": bool(output_compliance.get("matches_task", False)),
            "matched_outputs": output_compliance.get("matched_outputs", []) if isinstance(output_compliance.get("matched_outputs"), list) else [],
            "missing_outputs": output_compliance.get("missing_outputs", []) if isinstance(output_compliance.get("missing_outputs"), list) else [],
            "reason": str(output_compliance.get("reason", "")),
        },
        "reflection": {
            "reflection_score": max(0, min(10, int(reflection.get("reflection_score", 0) or 0))),
            "level": str(reflection.get("level", "")),
            "strengths": reflection.get("strengths", []) if isinstance(reflection.get("strengths"), list) else [],
            "problems": reflection.get("problems", []) if isinstance(reflection.get("problems"), list) else [],
        },
    }


def _enforce_output_requirements(
    analysis: Dict[str, Any],
    task: Dict[str, Any],
    final_report: str,
    reflection: str,
) -> Dict[str, Any]:
    """Apply deterministic checks for required report/reflection/task-specific outputs."""
    report = str(final_report or "").strip()
    reflection_text = str(reflection or "").strip()
    requirements = task.get("output_requirements", {}) if isinstance(task.get("output_requirements"), dict) else {}
    specific_output = str(requirements.get("specific_output", ""))
    required_outputs = [str(item) for item in requirements.get("required_outputs", []) or []]

    clarity = analysis.setdefault("clarity", {})
    if not report:
        clarity["clarity_score"] = 0
        clarity["structure"] = "缺失"
        clarity["is_missing_report"] = True
        problems = clarity.setdefault("problems", [])
        if "未提交最终报告" not in problems:
            problems.insert(0, "未提交最终报告")

    output = analysis.setdefault("output_compliance", {})
    missing = list(output.get("missing_outputs", []) if isinstance(output.get("missing_outputs"), list) else [])
    if not report:
        missing.append("最终成果报告")
    for keyword in OUTPUT_KEYWORDS:
        if keyword in specific_output and keyword not in report:
            missing.append(keyword)
    for item in required_outputs:
        if item and item not in report and item not in {"交互记录"}:
            missing.append(item)
    missing = list(dict.fromkeys(str(item) for item in missing if item))
    output["missing_outputs"] = missing
    output["matches_task"] = bool(report) and not missing
    if not output.get("reason"):
        output["reason"] = "根据任务指定成果要求与最终报告内容进行规则核验"

    if requirements.get("need_learning_reflection", True) and not reflection_text:
        reflection_obj = analysis.setdefault("reflection", {})
        reflection_obj["reflection_score"] = 0
        reflection_obj["level"] = "缺失"
        problems = reflection_obj.setdefault("problems", [])
        if "未提交学习反思" not in problems:
            problems.insert(0, "未提交学习反思")
    return analysis


def analyze_knowledge_semantic(
    task: Dict[str, Any],
    submission: Dict[str, Any],
    knowledge_points: List[Dict[str, Any]],
    related_ids: List[str],
    *,
    use_llm: bool = True,
) -> Dict[str, Any]:
    selected = _select_related_points(knowledge_points, related_ids)
    if not use_llm:
        return _enforce_output_requirements(
            _fallback_knowledge_analysis(task, submission, knowledge_points, related_ids),
            task,
            str(submission.get("final_report", "")),
            str(submission.get("reflection", "")),
        )
    try:
        data = call_llm(
            build_knowledge_prompt(
                task,
                selected,
                list(submission.get("dialogues", [])),
                str(submission.get("final_report", "")),
                str(submission.get("reflection", "")),
            )
        )
        return _enforce_output_requirements(
            _normalize_knowledge_analysis(data, selected),
            task,
            str(submission.get("final_report", "")),
            str(submission.get("reflection", "")),
        )
    except (LLMClientError, ValueError, TypeError, KeyError, re.error) as exc:
        fallback = _fallback_knowledge_analysis(task, submission, knowledge_points, related_ids)
        fallback["fallback_reason"] = str(exc)
        return _enforce_output_requirements(
            fallback,
            task,
            str(submission.get("final_report", "")),
            str(submission.get("reflection", "")),
        )
