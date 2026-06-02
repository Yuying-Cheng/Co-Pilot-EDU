"""成员4：交互质量分析与评分模块。"""
from .evaluator import evaluate_submission
from .evaluator_v2 import evaluate_submission_v2

__all__ = ["evaluate_submission", "evaluate_submission_v2"]
