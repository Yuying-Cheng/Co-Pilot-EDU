# learning_system/evaluator.py
"""
对外统一评阅入口。
修复：
1. _evaluate_v2 里正确区分 knowledge 和 task_data
2. validate_inputs 容错（见 evaluator/io_utils.py）
3. knowledge 为 None 或缺字段时降级到 LLM 单次评价，不崩溃
"""

import re
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import call_llm_json
from data_store import INTERACTION_TYPES


def evaluate_submission(submission: dict, task: dict = None, knowledge: dict = None) -> dict:
    """
    对外统一入口。
    - task 和 knowledge 都有效 → 走语义评价管道（v2）
    - 否则降级到 LLM 单次调用
    """
    if task and knowledge and _knowledge_is_valid(knowledge):
        try:
            return _evaluate_v2(submission, task, knowledge)
        except Exception as e:
            print(f"[evaluator] v2 失败，降级到 LLM 单次评价: {e}")

    return _evaluate_llm(submission, task, knowledge)


def _knowledge_is_valid(knowledge: dict) -> bool:
    """检查 knowledge 是否包含有效的知识点数据。"""
    if not isinstance(knowledge, dict):
        return False
    kps = knowledge.get("knowledge_points")
    return isinstance(kps, list) and len(kps) > 0


def _evaluate_v2(submission: dict, task: dict, knowledge: dict) -> dict:
    """调用结构化语义评价管道。"""
    from evaluator.evaluator_v2 import evaluate_submission_v2

    task_id = task.get("task_id", "task001")

    # ── 关键修复：正确构造 task_data，而不是把 knowledge 当 task_data ──────────
    # task_data 必须是 {"tasks": [task_dict]} 格式
    # knowledge 必须是包含 knowledge_points 的字典
    # 两者不能混用
    task_data = {"tasks": [task]}

    # 补充 task_data 里缺失的元数据，用 knowledge 里的信息
    if "course_name" not in task_data:
        task_data["course_name"] = knowledge.get("course_name", "未命名课程")
    if "chapter_id" not in task_data:
        task_data["chapter_id"] = knowledge.get("chapter_id", "ch_unknown")
    if "chapter_title" not in task_data:
        task_data["chapter_title"] = knowledge.get("chapter_title", "未命名章节")

    submission = dict(submission)
    submission.setdefault("task_id", task_id)
    submission.setdefault("chapter_id", knowledge.get("chapter_id", "ch01"))
    # 防止 student_id / student_name 缺失导致 validate_inputs 报错
    submission.setdefault("student_id", "unknown")
    submission.setdefault("student_name", "未知学生")

    result = evaluate_submission_v2(knowledge, task_data, submission, use_llm=True)

    # 字段对齐：UI 层用 comment / suggestions
    result.setdefault("comment", result.get("readable_comment", ""))
    result.setdefault("suggestions", result.get("improvement_suggestions", []))

    ia = result.get("interaction_analysis", {})
    ia.setdefault("total_rounds", len(submission.get("dialogues", [])))

    return result


# ── LLM 单次调用（降级兜底）────────────────────────────────────────────────────

EVAL_SYSTEM = """你是一位严格而公正的算法课程教学评估专家。
你需要从多个维度评估学生与大模型的交互记录，重点关注交互过程的质量，而非答案是否完美。
评估标准：
- 交互质量（50分）：是否有≥10轮有效交互、是否基于前一轮追问、是否使用多种交互方式、是否有深度和批判性思考
- 知识掌握（25分）：是否覆盖核心知识点、理解是否准确深入
- 成果呈现（15分）：最终报告是否清晰完整、逻辑是否严谨
- 学习反思（10分）：是否有真实的学习感悟和改进方向

请严格输出JSON格式，不添加任何解释文字。"""


def _evaluate_llm(submission: dict, task: dict = None, knowledge: dict = None) -> dict:
    dialogues = submission.get("dialogues", [])
    final_report = submission.get("final_report", "")
    reflection = submission.get("reflection", "")
    total_rounds = len(dialogues)
    dialogue_text = _format_dialogues(dialogues)

    task_desc = ""
    if task:
        task_desc = f"任务标题：{task.get('title', '')}\n任务要求：{task.get('description', '')}"

    kp_list = ""
    if knowledge and _knowledge_is_valid(knowledge):
        kps = knowledge.get("knowledge_points", [])
        kp_list = "核心知识点：" + "、".join(k.get("name", "") for k in kps[:8] if k.get("name"))

    prompt = f"""请评估以下学生的探究学习成果。

{task_desc}
{kp_list}

【对话记录】（共{total_rounds}轮）：
{dialogue_text[:6000]}

【最终成果报告】：
{final_report[:2000]}

【学习反思】：
{reflection[:1000]}

请输出如下JSON评估结果：
{{
  "total_score": 整数（0-100）,
  "scores": {{
    "interaction_quality": 整数（0-50）,
    "knowledge_mastery": 整数（0-25）,
    "presentation": 整数（0-15）,
    "reflection": 整数（0-10）
  }},
  "interaction_analysis": {{
    "total_rounds": {total_rounds},
    "valid_rounds": 估计有效轮数,
    "interaction_types": {{
      "询问": 0, "表达见解": 0, "审辨": 0,
      "猜想": 0, "想象": 0, "创新": 0, "苏格拉底回答": 0
    }},
    "has_follow_up": true或false,
    "has_questioning": true或false,
    "depth_level": "较浅|一般|较深|很深",
    "interaction_quality_details": "100字以内具体分析"
  }},
  "knowledge_analysis": {{
    "covered_points": [],
    "missing_points": [],
    "weak_points": []
  }},
  "comment": "综合评语150字以内",
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""

    try:
        return call_llm_json(EVAL_SYSTEM, prompt, max_tokens=3000)
    except Exception as e:
        # 最终兜底：返回一个空结构，不崩溃
        print(f"[evaluator] LLM 评阅也失败了: {e}")
        return {
            "total_score": 0,
            "scores": {"interaction_quality": 0, "knowledge_mastery": 0, "presentation": 0, "reflection": 0},
            "interaction_analysis": {
                "total_rounds": total_rounds, "valid_rounds": 0,
                "interaction_types": {t: 0 for t in INTERACTION_TYPES},
                "has_follow_up": False, "has_questioning": False, "depth_level": "较浅"
            },
            "knowledge_analysis": {"covered_points": [], "missing_points": [], "weak_points": []},
            "comment": f"评阅失败：{e}",
            "suggestions": ["请检查 API Key 配置和网络连接。"]
        }


def _format_dialogues(dialogues: list) -> str:
    lines = []
    for d in dialogues:
        r = d.get("round", "?")
        s = d.get("student_input", "").strip()
        m = d.get("model_output", "").strip()
        lines.append(f"[第{r}轮] 学生：{s[:200]}")
        lines.append(f"       模型：{m[:300]}")
    return "\n".join(lines)


def parse_dialogue_text(raw_text: str) -> list:
    """解析自由格式对话文本为结构化轮次列表。"""
    dialogues = []
    lines = raw_text.strip().split('\n')
    current_round = 0
    current_student = []
    current_model = []
    in_student = False
    in_model = False

    student_markers = ['学生：', '学生:', 'Q：', 'Q:', '用户：', '用户:']
    model_markers   = ['模型：', '模型:', 'A：', 'A:', 'Claude：', 'Claude:',
                       'AI：', 'AI:', 'ChatGPT：', 'ChatGPT:']

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        is_student = any(line_stripped.startswith(m) for m in student_markers)
        is_model   = any(line_stripped.startswith(m) for m in model_markers)

        if is_student:
            if current_student and current_model:
                current_round += 1
                dialogues.append({
                    "round": current_round,
                    "student_input": ' '.join(current_student).strip(),
                    "model_output":  ' '.join(current_model).strip(),
                })
                current_model = []
            current_student = []
            for m in student_markers:
                if line_stripped.startswith(m):
                    current_student.append(line_stripped[len(m):].strip())
                    break
            in_student, in_model = True, False

        elif is_model:
            current_model = []
            for m in model_markers:
                if line_stripped.startswith(m):
                    current_model.append(line_stripped[len(m):].strip())
                    break
            in_student, in_model = False, True

        else:
            if in_student:
                current_student.append(line_stripped)
            elif in_model:
                current_model.append(line_stripped)

    if current_student and current_model:
        current_round += 1
        dialogues.append({
            "round": current_round,
            "student_input": ' '.join(current_student).strip(),
            "model_output":  ' '.join(current_model).strip(),
        })

    # 兜底：段落解析
    if not dialogues:
        paras = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
        for i in range(0, len(paras) - 1, 2):
            dialogues.append({
                "round": i // 2 + 1,
                "student_input": paras[i],
                "model_output":  paras[i + 1] if i + 1 < len(paras) else "",
            })

    return dialogues