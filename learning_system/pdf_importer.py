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


def parse_pdf_to_submission(
    pdf_path: str,
    student_id: str = "",
    student_name: str = "",
    chapter_id: str = "ch01",
    task_id: str = "task001",
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

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    sid = student_id or f"stu_{base_name}"
    sname = student_name or f"学生_{base_name}"

    system_prompt = """你是一个专业的数据清洗助手。用户会提供一份学生提交的"课程探究任务"作业文本。
这份文本可能排版混乱，包含大量多余换行、错别字或缺失标点。

你的任务是：
1. 从中找出该学生的"十问十答"（对话记录），每问每答算一轮。
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
    }
