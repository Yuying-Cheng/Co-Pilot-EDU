"""Run the second-week semantic evaluator and write score.json."""
from __future__ import annotations

import argparse
from pathlib import Path

from evaluator.evaluator_v2 import evaluate_submission_v2
from evaluator.io_utils import load_json, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="成员4第二周：交互质量语义评价模块")
    parser.add_argument("--knowledge", required=True, help="knowledge.json 路径")
    parser.add_argument("--task", required=True, help="task.json 路径")
    parser.add_argument("--submission", required=True, help="student_submission.json 路径")
    parser.add_argument("--output", required=True, help="score.json 输出路径")
    parser.add_argument("--use-llm", action="store_true", help="启用 DeepSeek 语义分析；失败时自动使用规则兜底")
    args = parser.parse_args()

    result = evaluate_submission_v2(
        load_json(args.knowledge),
        load_json(args.task),
        load_json(args.submission),
        use_llm=args.use_llm,
    )
    save_json(result, args.output)
    mode = "DeepSeek语义分析" if result.get("llm_used") else "规则兜底分析"
    print(f"评分完成：{result['student_name']}，总分 {result['total_score']} 分，模式：{mode}")
    print(f"交互质量得分：{result['scores']['interaction_quality']} / 50")
    print(f"结果已保存：{Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
