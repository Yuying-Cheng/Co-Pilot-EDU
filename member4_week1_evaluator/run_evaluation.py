"""运行入口：使用三个 JSON 文件生成 score.json。"""
from __future__ import annotations
import argparse
from pathlib import Path
from evaluator import evaluate_submission
from evaluator.io_utils import load_json, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="成员4：学生交互质量分析与评分原型")
    parser.add_argument("--knowledge", required=True, help="knowledge.json 路径")
    parser.add_argument("--task", required=True, help="task.json 路径")
    parser.add_argument("--submission", required=True, help="student_submission.json 路径")
    parser.add_argument("--output", required=True, help="score.json 输出路径")
    args = parser.parse_args()
    result = evaluate_submission(load_json(args.knowledge), load_json(args.task), load_json(args.submission))
    save_json(result, args.output)
    print(f"评分完成：{result['student_name']}，总分 {result['total_score']} 分")
    print(f"交互质量得分：{result['scores']['interaction_quality']} / 50")
    print(f"结果已保存：{Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
