"""Second-week evaluation flow: rules for statistics, LLM for semantic evidence."""
from __future__ import annotations

from typing import Any, Dict

from .comment_generator_v2 import generate_feedback_v2
from .io_utils import find_task, validate_inputs
from .semantic_interaction_analyzer import analyze_interactions_semantic
from .semantic_knowledge_analyzer import analyze_knowledge_semantic
from .score_calculator_v2 import (
    calculate_interaction_quality_v2,
    calculate_knowledge_mastery_v2,
    calculate_presentation_v2,
    calculate_reflection_v2,
)
from .score_explainer_v2 import build_score_details


def evaluate_submission_v2(
    knowledge: Dict[str, Any],
    task_data: Dict[str, Any],
    submission: Dict[str, Any],
    *,
    use_llm: bool = True,
) -> Dict[str, Any]:
    validate_inputs(knowledge, task_data, submission)
    task = find_task(task_data, str(submission["task_id"]))
    knowledge_points = list(knowledge.get("knowledge_points", []))
    related_ids = [str(item) for item in task.get("related_knowledge_points", [])]

    interaction_analysis = analyze_interactions_semantic(task, submission, knowledge_points, use_llm=use_llm)
    knowledge_analysis = analyze_knowledge_semantic(task, submission, knowledge_points, related_ids, use_llm=use_llm)
    if not str(submission.get("reflection", "")).strip():
        knowledge_analysis["reflection"] = {
            "reflection_score": 0,
            "level": "缺失",
            "strengths": [],
            "problems": ["未提交学习反思"],
        }

    interaction_score, dimension_scores = calculate_interaction_quality_v2(task, interaction_analysis)
    interaction_analysis["dimension_scores"] = dimension_scores
    knowledge_score = calculate_knowledge_mastery_v2(knowledge_points, related_ids, knowledge_analysis)
    presentation_score = calculate_presentation_v2(knowledge_analysis)
    reflection_score = calculate_reflection_v2(knowledge_analysis)
    scores = {
        "interaction_quality": interaction_score,
        "knowledge_mastery": knowledge_score,
        "presentation": presentation_score,
        "reflection": reflection_score,
    }
    total_score = sum(scores.values())
    score_details = build_score_details(scores, interaction_analysis, knowledge_analysis)
    feedback = generate_feedback_v2(
        interaction_score,
        knowledge_score,
        presentation_score,
        reflection_score,
        interaction_analysis,
        knowledge_analysis,
    )

    return {
        "student_id": submission["student_id"],
        "student_name": submission["student_name"],
        "chapter_id": submission["chapter_id"],
        "chapter_title": knowledge.get("chapter_title",submission["chapter_id"]),
        "task_id": submission["task_id"],
        "total_score": total_score,
        "scores": scores,
        "score_details": score_details,
        "interaction_analysis": interaction_analysis,
        "knowledge_analysis": knowledge_analysis,
        "readable_comment": feedback["readable_comment"],
        "improvement_suggestions": feedback["improvement_suggestions"],
        "comment": feedback["comment"],
        "evaluator_version": "week2_semantic_v2",
        "llm_used": bool(interaction_analysis.get("llm_used")) and bool(knowledge_analysis.get("llm_used")),
    }
