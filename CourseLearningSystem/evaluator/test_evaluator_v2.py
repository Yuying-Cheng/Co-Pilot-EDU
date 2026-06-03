"""Tests for the second-week semantic evaluator fallback path."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluator import evaluate_submission_v2
import json


def _local_load_json(path_obj):
    with path_obj.open("r", encoding="utf-8") as f:
        return json.load(f)


class EvaluatorV2TestCase(unittest.TestCase):
    def setUp(self) -> None:
        data_dir = PROJECT_ROOT / "sample_data"
        self.knowledge = _local_load_json(data_dir / "knowledge.json")
        self.task = _local_load_json(data_dir / "task.json")
        self.good = _local_load_json(data_dir / "student_submission_good.json")
        self.shallow = _local_load_json(data_dir / "student_submission_shallow.json")
        self.brushing = _local_load_json(data_dir / "student_submission_brushing.json")

    def test_v2_output_keeps_legacy_fields_and_adds_dimensions(self) -> None:
        result = evaluate_submission_v2(self.knowledge, self.task, self.good, use_llm=False)
        for field in ["student_id", "student_name", "chapter_id", "task_id", "total_score", "scores", "interaction_analysis", "knowledge_analysis", "comment"]:
            self.assertIn(field, result)
        self.assertIn("readable_comment", result)
        self.assertIn("improvement_suggestions", result)
        self.assertIsInstance(result["improvement_suggestions"], list)
        self.assertIn("score_details", result)
        self.assertEqual(result["score_details"]["dimensions"]["interaction_quality"]["max_score"], 50)
        self.assertEqual(result["score_details"]["dimensions"]["interaction_quality"]["subdimensions"]["depth"]["max_score"], 15)
        self.assertIn("dimension_scores", result["interaction_analysis"])
        self.assertIn("evidence", result["interaction_analysis"])
        self.assertIn("knowledge_points", result["knowledge_analysis"])
        self.assertLessEqual(result["scores"]["interaction_quality"], 50)

    def test_v2_good_scores_higher_than_shallow_in_fallback(self) -> None:
        good_result = evaluate_submission_v2(self.knowledge, self.task, self.good, use_llm=False)
        shallow_result = evaluate_submission_v2(self.knowledge, self.task, self.shallow, use_llm=False)
        self.assertGreater(good_result["scores"]["interaction_quality"], shallow_result["scores"]["interaction_quality"])

    def test_brushing_rounds_are_penalized(self) -> None:
        result = evaluate_submission_v2(self.knowledge, self.task, self.brushing, use_llm=False)
        self.assertLess(result["scores"]["interaction_quality"], 30)
        self.assertEqual(result["scores"]["reflection"], 0)


if __name__ == "__main__":
    unittest.main()
