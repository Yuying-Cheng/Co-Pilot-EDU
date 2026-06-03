"""Parse student submissions from JSON, plain text, DOCX, or PDF files."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from parser.parser import read_docx, read_pdf, read_text_file


SUPPORTED_SUBMISSION_EXTS = {".json", ".txt", ".md", ".docx", ".pdf"}


def iter_submission_files(path: str) -> List[str]:
    target = Path(path)
    if target.is_file() and target.suffix.lower() in SUPPORTED_SUBMISSION_EXTS:
        return [str(target)]
    if not target.exists():
        return []
    files: List[str] = []
    for item in target.rglob("*"):
        if item.is_file() and item.suffix.lower() in SUPPORTED_SUBMISSION_EXTS:
            files.append(str(item))
    return sorted(files)


def _guess_identity(file_path: str, data: Dict[str, Any] | None = None) -> tuple[str, str]:
    data = data or {}
    stem = Path(file_path).stem
    student_id = str(data.get("student_id") or data.get("学号") or "").strip()
    student_name = str(data.get("student_name") or data.get("name") or data.get("姓名") or "").strip()
    if not student_id:
        match = re.search(r"(\d{6,})", stem)
        student_id = match.group(1) if match else stem
    if not student_name:
        cleaned = re.sub(r"[_\-\s]*(\d{6,}).*", "", stem).strip("_- ")
        student_name = cleaned or student_id
    return student_id, student_name


def _read_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in {".txt", ".md"}:
        return read_text_file(file_path)
    if ext == ".docx":
        return read_docx(file_path)
    if ext == ".pdf":
        return read_pdf(file_path)
    return ""


def _parse_dialogues(text: str) -> List[Dict[str, str]]:
    qa_dialogues = _parse_numbered_qa(text)
    if qa_dialogues:
        return qa_dialogues

    dialogues: List[Dict[str, str]] = []
    current: Dict[str, str] = {}
    student_patterns = ("学生：", "学生:", "我：", "我:", "User:", "user:", "Human:", "human:")
    model_patterns = ("模型：", "模型:", "AI：", "AI:", "Assistant:", "assistant:", "ChatGPT：", "ChatGPT:")

    def strip_prefix(line: str, prefixes: tuple[str, ...]) -> str:
        for prefix in prefixes:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        return line.strip()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(student_patterns):
            if current.get("student_input") and current.get("model_output"):
                dialogues.append(current)
                current = {}
            current["student_input"] = strip_prefix(line, student_patterns)
        elif line.startswith(model_patterns):
            current["model_output"] = strip_prefix(line, model_patterns)
            if current.get("student_input"):
                dialogues.append(current)
                current = {}
        elif current:
            key = "model_output" if current.get("model_output") else "student_input"
            current[key] = (current.get(key, "") + "\n" + line).strip()

    if current.get("student_input") and current.get("model_output"):
        dialogues.append(current)
    for index, item in enumerate(dialogues, start=1):
        item.setdefault("round", index)
    return dialogues


def _parse_numbered_qa(text: str) -> List[Dict[str, str]]:
    pattern = re.compile(
        r"(?:\*\*)?\s*(?:问|Q|问题)\s*(\d+)\s*(?:\*\*)?\s*[：:]\s*(.*?)"
        r"(?=(?:\*\*)?\s*(?:答|A|回答)\s*\1\s*(?:\*\*)?\s*[：:])"
        r"(?:\*\*)?\s*(?:答|A|回答)\s*\1\s*(?:\*\*)?\s*[：:]\s*(.*?)(?=(?:\*\*)?\s*(?:问|Q|问题)\s*\d+\s*(?:\*\*)?\s*[：:]|###|##|---|\Z)",
        flags=re.S | re.I,
    )
    dialogues: List[Dict[str, str]] = []
    for index, match in enumerate(pattern.finditer(text), start=1):
        question = _clean_block(match.group(2))
        answer = _clean_block(match.group(3))
        if question and answer:
            dialogues.append({"round": index, "student_input": question, "model_output": answer})
    if dialogues:
        return dialogues

    loose = re.compile(
        r"(?:\*\*)?\s*(?:问|Q|问题)\s*(\d+)\s*(?:\*\*)?\s*[：:]\s*(.*?)(?=(?:\*\*)?\s*(?:问|Q|问题|答|A|回答)\s*\d+\s*(?:\*\*)?\s*[：:]|\Z)",
        flags=re.S | re.I,
    )
    answers = {
        m.group(1): _clean_block(m.group(2))
        for m in re.finditer(
            r"(?:\*\*)?\s*(?:答|A|回答)\s*(\d+)\s*(?:\*\*)?\s*[：:]\s*(.*?)(?=(?:\*\*)?\s*(?:问|Q|问题|答|A|回答)\s*\d+\s*(?:\*\*)?\s*[：:]|\Z)",
            text,
            flags=re.S | re.I,
        )
    }
    for index, match in enumerate(loose.finditer(text), start=1):
        no = match.group(1)
        question = _clean_block(match.group(2))
        answer = answers.get(no, "")
        if question and answer:
            dialogues.append({"round": index, "student_input": question, "model_output": answer})
    return dialogues


def _clean_block(value: str) -> str:
    value = re.sub(r"\*\*", "", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _section_after(text: str, markers: List[str], stop_markers: List[str]) -> str:
    for marker in markers:
        pos = text.find(marker)
        if pos >= 0:
            start = pos + len(marker)
            tail = text[start:]
            stops = [tail.find(stop) for stop in stop_markers if tail.find(stop) >= 0]
            end = min(stops) if stops else len(tail)
            return tail[:end].strip(" ：:\n\r\t")
    return ""


def _parse_text_submission(file_path: str, chapter_id: str, task_id: str) -> Dict[str, Any]:
    text = _read_text(file_path)
    dialogues = _parse_dialogues(text)
    final_report = _section_after(
        text,
        ["成果报告", "最终报告", "学习成果", "理解总结", "知识总结", "探究报告"],
        ["学习反思", "个人心得", "学习心得", "心得体会"],
    )
    if not final_report:
        final_report = _section_after(
            text,
            ["任务一总结", "任务二总结", "任务三总结", "总结"],
            ["---", "## 任务", "学习反思", "个人心得", "学习心得", "心得体会"],
        )
    reflection = _section_after(
        text,
        ["学习反思", "个人心得", "学习心得", "心得体会"],
        [],
    )
    if not final_report:
        final_report = re.sub(r"(学生|模型|AI|Assistant|User)[：:].*", "", text).strip()
    student_id, student_name = _guess_identity(file_path)
    return {
        "student_id": student_id,
        "student_name": student_name,
        "chapter_id": chapter_id,
        "task_id": task_id,
        "dialogues": dialogues,
        "final_report": final_report,
        "reflection": reflection,
        "source_file": file_path,
        "raw_text": text,
    }


def parse_submission_file(file_path: str, chapter_id: str, task_id: str) -> Dict[str, Any]:
    ext = Path(file_path).suffix.lower()
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        student_id, student_name = _guess_identity(file_path, data)
        data.setdefault("student_id", student_id)
        data.setdefault("student_name", student_name)
        data.setdefault("chapter_id", chapter_id)
        data.setdefault("task_id", task_id)
        data.setdefault("dialogues", [])
        data.setdefault("final_report", "")
        data.setdefault("reflection", "")
        data["source_file"] = file_path
        data.setdefault("raw_text", json.dumps(data, ensure_ascii=False))
        return data
    return _parse_text_submission(file_path, chapter_id, task_id)
