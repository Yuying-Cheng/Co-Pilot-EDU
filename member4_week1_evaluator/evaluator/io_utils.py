"""JSON 读取、保存与基本接口校验。"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: str | Path) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象：{file_path}")
    return data


def save_json(data: Dict[str, Any], path: str | Path) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def validate_inputs(knowledge: Dict[str, Any], task_data: Dict[str, Any], submission: Dict[str, Any]) -> None:
    required_knowledge = ["course_name", "chapter_id", "chapter_title", "knowledge_points"]
    required_submission = ["student_id", "student_name", "chapter_id", "task_id", "dialogues"]
    for field in required_knowledge:
        if field not in knowledge:
            raise ValueError(f"knowledge.json 缺少字段：{field}")
    if not isinstance(task_data.get("tasks"), list) or not task_data["tasks"]:
        raise ValueError("task.json 中 tasks 必须为非空列表")
    for field in required_submission:
        if field not in submission:
            raise ValueError(f"student_submission.json 缺少字段：{field}")
    if not isinstance(submission["dialogues"], list):
        raise ValueError("student_submission.json 中 dialogues 必须为列表")


def find_task(task_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in task_data.get("tasks", []):
        if task.get("task_id") == task_id:
            return task
    raise ValueError(f"task.json 中未找到任务：{task_id}")
