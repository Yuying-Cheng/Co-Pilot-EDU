"""
PDF Importer: parse student submission PDFs → structured submission dicts.
Uses PyMuPDF for text extraction and DeepSeek LLM to structure the content.
"""

import os
import re
from llm_client import get_client


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a student PDF submission using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        return "\n".join(page.get_text("text") for page in doc)
    except ImportError:
        import PyPDF2
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)


def _normalize_space(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text or "").strip()


def _parse_turn_style_dialogues(raw_text: str) -> list:
    """Parse exported AI chat logs that use `Turn N / User / Assistant` blocks."""
    pattern = re.compile(
        r"Turn\s+(\d+)\s+(?:👤\s*)?User\s*(.*?)\s*(?:🤖\s*)?Assistant\s*(.*?)(?=\nTurn\s+\d+\s+(?:👤\s*)?User|\Z)",
        re.S | re.I,
    )
    dialogues = []
    for match in pattern.finditer(raw_text):
        user = _normalize_space(match.group(2))
        assistant = _normalize_space(match.group(3))
        user = re.sub(r"^\[This turn includes uploaded pdfs\]\s*(PDF\s*)*", "", user, flags=re.I).strip()
        if user and assistant:
            dialogues.append({
                "round": len(dialogues) + 1,
                "student_input": user,
                "model_output": assistant,
            })
    return dialogues


def _parse_qa_style_dialogues(raw_text: str) -> list:
    """Parse homework documents that use 问1/答1 or **问1**/**答1** pairs."""
    pattern = re.compile(
        r"(?:\*\*)?\s*问\s*(\d+)\s*(?:\*\*)?\s*[：:]\s*(.*?)"
        r"(?:\*\*)?\s*答\s*\1\s*(?:\*\*)?\s*[：:]\s*(.*?)(?=(?:\*\*)?\s*问\s*\d+\s*(?:\*\*)?\s*[：:]|###|##|---|\Z)",
        re.S,
    )
    dialogues = []
    for match in pattern.finditer(raw_text):
        student = _normalize_space(match.group(2))
        model = _normalize_space(match.group(3))
        if student and model:
            dialogues.append({
                "round": len(dialogues) + 1,
                "student_input": student,
                "model_output": model,
            })
    return dialogues


def _extract_section(raw_text: str, headings: list[str]) -> str:
    heading_pattern = "|".join(re.escape(h) for h in headings)
    match = re.search(
        rf"(?:###?\s*)?(?:{heading_pattern})\s*[：:]?\s*(.*?)(?=\n\s*(?:#{1,3}\s*)?(?:任务[一二三四五六七八九十\d]+|十问十答|学习反思|心得|---)|\Z)",
        raw_text,
        re.S,
    )
    return _normalize_space(match.group(1)) if match else ""


def _extract_declared_turn_count(raw_text: str) -> int:
    turn_match = re.search(r"\bTurns\s*[:：]\s*(\d+)", raw_text, re.I)
    if turn_match:
        return int(turn_match.group(1))
    turn_numbers = [int(x) for x in re.findall(r"\bTurn\s+(\d+)\b", raw_text, re.I)]
    qa_numbers = [int(x) for x in re.findall(r"问\s*(\d+)\s*[：:]", raw_text)]
    return max(turn_numbers + qa_numbers + [0])


def _extract_student_identity(raw_text: str) -> tuple[str, str]:
    """Extract student id and name from common homework header formats."""
    text = raw_text or ""
    compact = re.sub(r"[ \t]+", " ", text)
    sid = ""
    name = ""

    id_patterns = [
        r"(?:学号|学生编号|Student\s*ID|ID)\s*[：:]\s*([A-Za-z0-9_\-]{4,30})",
        r"(?:学号|学生编号)\s+([A-Za-z0-9_\-]{4,30})",
    ]
    name_patterns = [
        r"(?:姓名|学生姓名|Name)\s*[：:]\s*([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z·\s]{1,20})",
        r"(?:姓名|学生姓名)\s+([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z·\s]{1,20})",
    ]

    for pattern in id_patterns:
        match = re.search(pattern, compact, re.I)
        if match:
            sid = match.group(1).strip()
            break

    for pattern in name_patterns:
        match = re.search(pattern, compact, re.I)
        if match:
            name = match.group(1).strip()
            name = re.split(r"\s*(?:学号|学生编号|班级|课程|任务|章节|提交时间|日期|$)\s*", name)[0].strip()
            break

    table_match = re.search(
        r"姓名\s*[：:\s]\s*([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z·\s]{1,20})"
        r".{0,40}?学号\s*[：:\s]\s*([A-Za-z0-9_\-]{4,30})",
        compact,
        re.S,
    )
    if table_match:
        name = name or table_match.group(1).strip()
        sid = sid or table_match.group(2).strip()

    return sid, name


def _parse_pdf_locally(raw_text: str) -> dict:
    dialogues = _parse_turn_style_dialogues(raw_text)
    if not dialogues:
        dialogues = _parse_qa_style_dialogues(raw_text)
    return {
        "dialogues": dialogues,
        "final_report": _extract_section(raw_text, ["任务一总结", "总结报告", "任务总结", "最终报告", "探究报告"]),
        "reflection": _extract_section(raw_text, ["学习反思", "个人学习心得", "心得体会", "学习心得", "反思"]),
        "source_total_turns": _extract_declared_turn_count(raw_text),
    }


def parse_pdf_to_submission(
    pdf_path: str,
    student_id: str = "",
    student_name: str = "",
    chapter_id: str = "ch01",
    task_id: str = "task001",
    fallback_index: int | None = None,
) -> dict:
    """
    Parse a single student submission PDF into a structured submission dict.
    The LLM extracts dialogues, final_report, and reflection from the messy PDF text.

    Args:
        pdf_path: Path to the student's PDF file.
        student_id: Overrides auto-generated ID if provided.
        student_name: Overrides auto-generated name if provided.
        chapter_id: Chapter this submission belongs to.
        task_id: Task this submission targets.

    Returns:
        A submission dict compatible with data_store.save_submission().
        Raises RuntimeError on parsing failure.
    """
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise RuntimeError(f"PDF 无法提取文字，可能是扫描件：{os.path.basename(pdf_path)}")

    extracted_sid, extracted_name = _extract_student_identity(raw_text)
    fallback_no = fallback_index if fallback_index is not None else 1
    sid = student_id or extracted_sid or f"stu_{fallback_no}"
    sname = student_name or extracted_name or f"学生_{fallback_no}"

    local = _parse_pdf_locally(raw_text)
    if local["dialogues"]:
        return {
            "student_id": sid,
            "student_name": sname,
            "chapter_id": chapter_id,
            "task_id": task_id,
            "dialogues": local["dialogues"],
            "final_report": local.get("final_report", ""),
            "reflection": local.get("reflection", ""),
            "source_total_turns": local.get("source_total_turns", len(local["dialogues"])),
            "_parse_method": "rule",
        }

    system_prompt = """你是一个专业的数据清洗助手。用户会提供一份学生提交的"课程探究任务"作业文本。
这份文本可能排版混乱，包含大量多余换行、错别字或缺失标点。

你的任务是：
1. 从中找出该学生的"十问十答"或 Turn/User/Assistant 对话记录，每问每答或每个 Turn 算一轮，不要合并多个 Turn。
2. 找出该任务的总结报告（final_report）。
3. 找出整体学习反思（reflection）。
4. 严格以下面的 JSON 格式输出，不要输出任何 Markdown 标记，直接输出合法 JSON：

{
    "dialogues": [
        {"round": 1, "student_input": "学生的问题", "model_output": "大模型的回答"},
        {"round": 2, "student_input": "...", "model_output": "..."}
    ],
    "final_report": "提取到的任务总结",
    "reflection": "提取到的整体反思"
}

注意：如果某些内容找不到，对应字段留空字符串或空数组，但保证 JSON 结构完整。"""

    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请提取以下作业内容：\n{raw_text[:8000]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    result_str = response.choices[0].message.content
    result_str = re.sub(r'^```json\s*|\s*```$', '', result_str.strip())

    import json
    extracted = json.loads(result_str)

    return {
        "student_id": sid,
        "student_name": sname,
        "chapter_id": chapter_id,
        "task_id": task_id,
        "dialogues": extracted.get("dialogues", []),
        "final_report": extracted.get("final_report", ""),
        "reflection": extracted.get("reflection", ""),
        "source_total_turns": _extract_declared_turn_count(raw_text),
        "_parse_method": "llm",
    }
