"""JSON 读取、保存与基本接口校验。
修复：knowledge.json 缺少 course_name / chapter_id / chapter_title 时自动补默认值，
      不再硬性报错——这些字段对评分逻辑本身无影响，只是元数据。
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


def validate_inputs(
    knowledge: Dict[str, Any],
    task_data: Dict[str, Any],
    submission: Dict[str, Any],
) -> None:
    """
    校验输入数据完整性。
    对 knowledge 中的元数据字段（course_name / chapter_id / chapter_title）做容错补全，
    而不是直接抛异常——缺少这些字段不影响评分，但缺少 knowledge_points 才是真正的问题。
    """
    # ── knowledge 容错补全 ────────────────────────────────────────────────────
    # 从 chapter_id 或 submission 里推断缺失的元数据
    if "course_name" not in knowledge or not knowledge["course_name"]:
        # 优先用 task_data 里的课程名，其次用 submission 里的章节，最后给默认值
        fallback = (
            task_data.get("course_name")
            or submission.get("chapter_id", "")
            or "未命名课程"
        )
        knowledge["course_name"] = fallback

    if "chapter_id" not in knowledge or not knowledge["chapter_id"]:
        knowledge["chapter_id"] = (
            submission.get("chapter_id")
            or task_data.get("chapter_id", "ch_unknown")
        )

    if "chapter_title" not in knowledge or not knowledge["chapter_title"]:
        knowledge["chapter_title"] = (
            task_data.get("chapter_title")
            or knowledge.get("chapter_id", "未命名章节")
        )

    # knowledge_points 必须存在且非空，这才是评分的核心数据
    if not knowledge.get("knowledge_points"):
        raise ValueError(
            "knowledge.json 中缺少 knowledge_points 字段，"
            "请确认已完成「课件导入 → 提取知识点」流程。"
        )

    # ── task_data 校验 ────────────────────────────────────────────────────────
    if not isinstance(task_data.get("tasks"), list) or not task_data["tasks"]:
        raise ValueError(
            "task.json 中 tasks 必须为非空列表，"
            "请确认已完成「课件导入 → 生成任务」流程。"
        )

    # ── submission 校验 ───────────────────────────────────────────────────────
    required_submission = ["student_id", "student_name", "chapter_id", "task_id", "dialogues"]
    for field in required_submission:
        if field not in submission:
            raise ValueError(f"提交数据缺少字段：{field}")

    if not isinstance(submission["dialogues"], list):
        raise ValueError("submission 中 dialogues 必须为列表")


def find_task(task_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """在 task_data 中找到指定 task_id 的任务，找不到时返回第一个任务而非报错。"""
    for task in task_data.get("tasks", []):
        if task.get("task_id") == task_id:
            return task
    # 找不到时兜底返回第一个任务，避免因 task_id 不匹配而中断
    tasks = task_data.get("tasks", [])
    if tasks:
        return tasks[0]
    raise ValueError(f"task.json 中未找到任务：{task_id}，且任务列表为空。")


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