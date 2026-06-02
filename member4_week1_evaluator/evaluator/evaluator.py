"""成员4主流程：三个输入 JSON 生成 score.json。"""
from __future__ import annotations
from typing import Any, Dict
from .comment_generator import generate_comment
from .interaction_analyzer import analyze_interactions
from .io_utils import find_task, validate_inputs
from .knowledge_analyzer import analyze_knowledge
from .score_calculator import calculate_interaction_quality, calculate_knowledge_mastery, calculate_presentation, calculate_reflection


def evaluate_submission(knowledge: Dict[str, Any], task_data: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
    validate_inputs(knowledge, task_data, submission)
    task = find_task(task_data, str(submission["task_id"]))
    knowledge_points = list(knowledge.get("knowledge_points", []))
    related_ids = list(task.get("related_knowledge_points", []))
    interaction_internal = analyze_interactions(submission["dialogues"], knowledge_points)
    knowledge_analysis = analyze_knowledge(submission, knowledge_points, related_ids)
    interaction_score = calculate_interaction_quality(task, interaction_internal)
    knowledge_score = calculate_knowledge_mastery(knowledge_points, related_ids, knowledge_analysis)
    presentation_score = calculate_presentation(str(submission.get("final_report", "")), len(knowledge_analysis["covered_points"]))
    reflection_score = calculate_reflection(str(submission.get("reflection", "")))
    total_score = interaction_score + knowledge_score + presentation_score + reflection_score
    interaction_analysis = {
        "total_rounds": interaction_internal["total_rounds"],
        "valid_rounds": interaction_internal["valid_rounds"],
        "interaction_types": interaction_internal["interaction_types"],
        "has_follow_up": interaction_internal["has_follow_up"],
        "has_questioning": interaction_internal["has_questioning"],
        "depth_level": interaction_internal["depth_level"],
    }
    return {
        "student_id": submission["student_id"],
        "student_name": submission["student_name"],
        "chapter_id": submission["chapter_id"],
        "task_id": submission["task_id"],
        "total_score": total_score,
        "scores": {
            "interaction_quality": interaction_score,
            "knowledge_mastery": knowledge_score,
            "presentation": presentation_score,
            "reflection": reflection_score,
        },
        "interaction_analysis": interaction_analysis,
        "knowledge_analysis": knowledge_analysis,
        "comment": generate_comment(interaction_score, interaction_internal, knowledge_analysis),
    }
