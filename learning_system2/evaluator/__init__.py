"""成员4：交互质量分析与评分模块。"""
from .evaluator_v2 import evaluate_submission_v2
from .io_utils import parse_dialogue_text


def _knowledge_is_valid(knowledge: dict) -> bool:
    if not isinstance(knowledge, dict):
        return False
    kps = knowledge.get("knowledge_points")
    return isinstance(kps, list) and len(kps) > 0


def evaluate_submission(submission, task=None, knowledge=None):
    """
    兼容 UI 层调用方式：evaluate_submission(submission, task, knowledge)
    当 knowledge 有效时优先走语义评分 v2，否则降级到规则评分 v1。
    """
    submission = dict(submission)
    submission.setdefault("student_id", "unknown")
    submission.setdefault("student_name", "未知学生")
    if task:
        submission.setdefault("task_id", task.get("task_id", "task001"))
    if knowledge:
        submission.setdefault("chapter_id", knowledge.get("chapter_id", "ch01"))

    task_data = {"tasks": [task]} if task else {"tasks": []}

    if task and knowledge and _knowledge_is_valid(knowledge):
        try:
            return evaluate_submission_v2(knowledge, task_data, submission, use_llm=True)
        except Exception as e:
            print(f"[evaluator] v2 失败，降级到规则评分: {e}")

    from .evaluator import evaluate_submission as _v1
    return _v1(knowledge, task_data, submission)


__all__ = ["evaluate_submission", "evaluate_submission_v2", "parse_dialogue_text"]
