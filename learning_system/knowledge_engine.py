"""
Knowledge engine: extract structured knowledge points from course text.
Integrates member2's KnowledgeEngine logic; API key is managed by llm_client.
"""

import json
import re
from llm_client import get_api_key

from openai import OpenAI

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def _get_client() -> OpenAI:
    key = get_api_key()
    if not key:
        raise RuntimeError("未配置 API Key，请先在设置页填写。")
    return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)


def generate_knowledge_base(raw_text: str, course_name: str, chapter_title: str) -> dict:
    """
    Extract structured knowledge points from raw course text.
    Returns a knowledge.json-compatible dict.
    """
    client = _get_client()
    system_prompt = """你是一个严谨的计算机课程助教。请阅读用户提供的课件文本，提取核心知识体系。

要求：
1. 知识点层级分明：涵盖 concept(核心概念), algorithm(重点算法), difficulty(难点/易错点), application(应用延伸)
2. 明确区分重要度：core(核心重点，必考), important(重要), extended(扩展了解)
3. 生成一段精炼的 summary 摘要，概括本章重点掌握的核心脉络
4. 提取5-12个知识点，按重要性排序

请严格以下列 JSON 格式输出，不要包含任何 Markdown 标记：
{
  "course_name": "课程名称",
  "chapter_id": "如 ch01",
  "chapter_title": "章节标题",
  "summary": "本章重点掌握：1. ... 2. ...",
  "knowledge_points": [
    {
      "id": "kp001",
      "name": "知识点名称",
      "type": "concept | algorithm | difficulty | application",
      "importance": "core | important | extended",
      "description": "详细说明（50-100字）"
    }
  ]
}"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"课程名称：{course_name}\n章节：{chapter_title}\n课件内容：\n{raw_text[:8000]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    result_str = response.choices[0].message.content
    result_str = re.sub(r'^```json\s*|\s*```$', '', result_str.strip())
    return json.loads(result_str)


def calculate_coverage(knowledge_points: list, submission_data: dict) -> dict:
    """
    Analyse which knowledge points the student covered/missed/is weak on.
    Returns: {"covered_points": [ids], "missing_points": [ids], "weak_points": [names]}
    """
    client = _get_client()

    # Build student text from dialogues + report + reflection
    texts = []
    for d in submission_data.get("dialogues", []):
        if d.get("student_input"):
            texts.append(f"【学生发言】: {d['student_input']}")
    if submission_data.get("final_report"):
        texts.append(f"【最终报告】: {submission_data['final_report']}")
    if submission_data.get("reflection"):
        texts.append(f"【学习反思】: {submission_data['reflection']}")
    student_text = "\n".join(texts)

    kp_simplified = [{"id": kp["id"], "name": kp["name"]} for kp in knowledge_points]

    system_prompt = """你是一个严谨的 AI 助教。对比【学生输出】和【知识点库】，对每个知识点逐一排查。

判断标准：
1. covered：学生准确表达了该知识点，或进行了有效质疑、猜想
2. missing：学生完全没有提及
3. weak：学生提到了，但理解存在明显偏差或表述极度肤浅

严格输出以下 JSON 格式：
{
    "analysis_details": [
        {"id": "kp001", "name": "知识点名称", "evidence": "证据原文，没提到写未提及", "status": "covered | missing | weak"}
    ]
}"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【知识点库】:\n{json.dumps(kp_simplified, ensure_ascii=False)}\n\n【学生输出】:\n{student_text[:4000]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    result_str = re.sub(r'^```json\s*|\s*```$', '', response.choices[0].message.content.strip())
    analysis_result = json.loads(result_str)

    output = {"covered_points": [], "missing_points": [], "weak_points": []}
    for item in analysis_result.get("analysis_details", []):
        if item["status"] == "covered":
            output["covered_points"].append(item["id"])
        elif item["status"] == "missing":
            output["missing_points"].append(item["id"])
        elif item["status"] == "weak":
            output["weak_points"].append(item.get("name", item["id"]))
    return output