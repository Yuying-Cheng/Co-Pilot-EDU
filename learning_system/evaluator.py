"""
Evaluate student interaction quality and generate scores.
Routes to member4's evaluate_submission_v2 (semantic LLM evaluation) with
a rule-based fallback when the evaluator package or LLM is unavailable.
"""

import re
import json
from llm_client import call_llm_json
from data_store import INTERACTION_TYPES


EVAL_SYSTEM = """你是一位严格而公正的算法课程教学评估专家。
你需要从多个维度评估学生与大模型的交互记录，重点关注交互过程的质量，而非答案是否完美。
评估标准：
- 交互质量（50分）：是否有≥10轮有效交互、是否基于前一轮追问、是否使用多种交互方式、是否有深度和批判性思考
- 知识掌握（25分）：是否覆盖核心知识点、理解是否准确深入
- 成果呈现（15分）：最终报告是否清晰完整、逻辑是否严谨
- 学习反思（10分）：是否有真实的学习感悟和改进方向

请严格输出JSON格式，不添加任何解释文字。"""


def evaluate_submission(submission: dict, task: dict = None, knowledge: dict = None) -> dict:
    """
    Evaluate a student submission.
    Tries member4's evaluate_submission_v2 first; falls back to LLM-based evaluation.
    """
    # Try the full member4 v2 evaluator when both task and knowledge are available
    if task and knowledge:
        try:
            return _evaluate_v2(submission, task, knowledge)
        except Exception:
            pass  # Fall through to simpler LLM evaluation

    return _evaluate_llm(submission, task, knowledge)


def _evaluate_v2(submission: dict, task: dict, knowledge: dict) -> dict:
    """Use member4's evaluate_submission_v2 (semantic LLM pipeline)."""
    from evaluator.evaluator_v2 import evaluate_submission_v2

    # evaluate_submission_v2 expects task_data with a "tasks" list
    task_id = task.get("task_id", "task001")
    task_data = {"tasks": [task]}
    submission = dict(submission)
    submission.setdefault("task_id", task_id)
    submission.setdefault("chapter_id", knowledge.get("chapter_id", "ch01"))

    result = evaluate_submission_v2(knowledge, task_data, submission, use_llm=True)

    # Normalise output to what the UI expects
    result.setdefault("comment", result.get("readable_comment", ""))
    result.setdefault("suggestions", result.get("improvement_suggestions", []))
    ia = result.get("interaction_analysis", {})
    if "total_rounds" not in ia:
        ia["total_rounds"] = len(submission.get("dialogues", []))
    return result


def _evaluate_llm(submission: dict, task: dict = None, knowledge: dict = None) -> dict:
    """Fallback: single LLM call evaluation."""
    dialogues = submission.get("dialogues", [])
    final_report = submission.get("final_report", "")
    reflection = submission.get("reflection", "")

    total_rounds = len(dialogues)
    dialogue_text = _format_dialogues(dialogues)

    task_desc = ""
    if task:
        task_desc = f"任务标题：{task.get('title','')}\n任务要求：{task.get('description','')}"

    kp_list = ""
    if knowledge:
        kps = knowledge.get("knowledge_points", [])
        kp_list = "核心知识点：" + "、".join(k["name"] for k in kps[:8])

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
    "valid_rounds": 估计有效轮数（整数）,
    "interaction_types": {{
      "询问": 次数,
      "表达见解": 次数,
      "审辨": 次数,
      "猜想": 次数,
      "想象": 次数,
      "创新": 次数,
      "苏格拉底回答": 次数
    }},
    "has_follow_up": true或false,
    "has_questioning": true或false,
    "depth_level": "较浅|一般|较深|很深",
    "interaction_quality_details": "对交互质量的具体分析（100字以内）"
  }},
  "knowledge_analysis": {{
    "covered_points": ["知识点名称列表"],
    "missing_points": ["未涉及的知识点"],
    "weak_points": ["理解薄弱的知识点"]
  }},
  "comment": "综合评语（150字以内，指出优点和不足）",
  "suggestions": ["改进建议1", "改进建议2", "改进建议3"]
}}

评分要严格：
- 如果交互少于10轮，交互质量不超过25分
- 如果交互方式单一（只有询问），交互质量不超过30分
- 如果存在明显的"直接要答案"而非探究的情况，扣分
- "说人话"的自然交互比复制粘贴的格式化提问要加分"""

    return call_llm_json(EVAL_SYSTEM, prompt, max_tokens=3000)


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
    """
    Parse free-form dialogue text into structured rounds.
    Supports: 学生：/模型：, Q:/A:, 用户:/AI: etc.
    """
    dialogues = []
    lines = raw_text.strip().split('\n')
    current_round = 0
    current_student = []
    current_model = []
    in_student = False
    in_model = False

    student_markers = ['学生：', '学生:', 'Q：', 'Q:', '用户：', '用户:']
    model_markers = ['模型：', '模型:', 'A：', 'A:', 'Claude：', 'Claude:', 'AI：', 'AI:']

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        is_student = any(line_stripped.startswith(m) for m in student_markers)
        is_model = any(line_stripped.startswith(m) for m in model_markers)

        if is_student:
            if current_student and current_model:
                current_round += 1
                dialogues.append({
                    "round": current_round,
                    "student_input": ' '.join(current_student).strip(),
                    "model_output": ' '.join(current_model).strip()
                })
                current_model = []
            current_student = []
            for m in student_markers:
                if line_stripped.startswith(m):
                    current_student.append(line_stripped[len(m):].strip())
                    break
            in_student = True
            in_model = False

        elif is_model:
            current_model = []
            for m in model_markers:
                if line_stripped.startswith(m):
                    current_model.append(line_stripped[len(m):].strip())
                    break
            in_student = False
            in_model = True

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
            "model_output": ' '.join(current_model).strip()
        })

    # Fallback: paragraph-based parsing
    if not dialogues:
        paras = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
        for i in range(0, len(paras) - 1, 2):
            dialogues.append({
                "round": i // 2 + 1,
                "student_input": paras[i],
                "model_output": paras[i + 1] if i + 1 < len(paras) else ""
            })

    return dialogues