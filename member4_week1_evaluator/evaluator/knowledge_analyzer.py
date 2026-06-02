"""初版知识点覆盖分析。"""
from __future__ import annotations
from typing import Any, Dict, List


def analyze_knowledge(submission: Dict[str, Any], knowledge_points: List[Dict[str, Any]], related_ids: List[str]) -> Dict[str, List[str]]:
    selected_points = [point for point in knowledge_points if not related_ids or point.get("id") in related_ids]
    student_text_parts = [str(dialogue.get("student_input", "")) for dialogue in submission.get("dialogues", [])]
    student_text_parts += [str(submission.get("final_report", "")), str(submission.get("reflection", ""))]
    combined_text = "\n".join(student_text_parts)
    covered_points: List[str] = []
    missing_points: List[str] = []
    weak_points: List[str] = []
    for point in selected_points:
        point_id = str(point.get("id", ""))
        name = str(point.get("name", ""))
        if name and name in combined_text:
            covered_points.append(point_id)
        else:
            missing_points.append(point_id)
            if point.get("importance") in {"core", "important"}:
                weak_points.append(name)
    return {"covered_points": covered_points, "missing_points": missing_points, "weak_points": weak_points}
