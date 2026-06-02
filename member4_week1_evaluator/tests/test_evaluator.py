"""成员4评价模块最小测试。"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from evaluator import evaluate_submission
from evaluator.io_utils import load_json


class EvaluatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        data_dir = PROJECT_ROOT / "sample_data"
        self.knowledge = load_json(data_dir / "knowledge.json")
        self.task = load_json(data_dir / "task.json")
        self.good = load_json(data_dir / "student_submission_good.json")
        self.shallow = load_json(data_dir / "student_submission_shallow.json")

    def test_output_schema(self) -> None:
        result = evaluate_submission(self.knowledge, self.task, self.good)
        for field in ["student_id", "student_name", "chapter_id", "task_id", "total_score", "scores", "interaction_analysis", "knowledge_analysis", "comment"]:
            self.assertIn(field, result)
        self.assertLessEqual(result["scores"]["interaction_quality"], 50)

    def test_deep_dialogue_scores_higher_than_shallow_dialogue(self) -> None:
        good_result = evaluate_submission(self.knowledge, self.task, self.good)
        shallow_result = evaluate_submission(self.knowledge, self.task, self.shallow)
        self.assertGreater(good_result["scores"]["interaction_quality"], shallow_result["scores"]["interaction_quality"])
        self.assertTrue(good_result["interaction_analysis"]["has_questioning"])
        self.assertFalse(shallow_result["interaction_analysis"]["has_questioning"])


if __name__ == "__main__":
    unittest.main()
