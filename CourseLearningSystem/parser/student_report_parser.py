import fitz  # PyMuPDF
import json
import os
import re
from openai import OpenAI

from data.data_manager import save_report


def extract_text_from_pdf(pdf_path: str) -> str:
    """从 PDF 提取原始文本"""
    try:
        doc = fitz.open(pdf_path)
        raw_text = ""
        for page in doc:
            raw_text += page.get_text("text")
        return raw_text
    except Exception as e:
        print(f"❌ 读取 PDF 失败: {pdf_path} ({e})")
        return ""


def call_llm_for_extraction(text: str, api_key: str) -> dict:
    """调用 DeepSeek 进行智能提取"""
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    system_prompt = """
    你是一个专业的数据清洗助手。用户会提供一份学生提交的“课程探究任务”作业文本。
    这份文本可能排版极其混乱，包含大量多余换行、错别字或缺失标点。

    你的任务是：
    1. 从中找出该学生的“十问十答”（对话记录）。
    2. 找出该任务的总结（final_report）。
    3. 找出整体反思（reflection）。
    4. 严格以下面的 JSON 格式输出，不要输出任何 Markdown 标记，直接输出合法的 JSON 字符串：

    {
        "dialogues": [
            {"round": 1, "student_input": "学生的问题", "model_output": "大模型的回答"},
            {"round": 2, "student_input": "学生的问题", "model_output": "大模型的回答"}
        ],
        "final_report": "提取到的任务一总结",
        "reflection": "提取到的整体反思"
    }

    注意：如果某些内容实在找不到，对应字段留空字符串或空数组，但保证 JSON 结构完整。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请提取以下作业内容：\n{text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # 温度极低，保证稳定性
        )

        result_str = response.choices[0].message.content
        result_str = re.sub(r'^```json\s*', '', result_str)
        result_str = re.sub(r'\s*```$', '', result_str)

        return json.loads(result_str)

    except Exception as e:
        print(f"❌ API 调用或解析失败: {e}")
        return None


def process_student_report(pdf_path: str, student_id: str, chapter_id: str, api_key: str):
    """
    处理单个学生的 PDF 作业报告，提取结构化数据并保存。
    专供主控流水线或 UI 界面调用。
    """
    base_name = os.path.basename(pdf_path)
    print(f"⏳ 正在智能解析学生报告: {base_name} ...")

    # 提取文本
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        print(f"⚠️ 警告: {base_name} 提取不到任何文字，可能是纯图片扫描件！")
        return False

    # 丢给大模型处理 (截取前 8000 字符防止超出 token 限制)
    extracted_data = call_llm_for_extraction(raw_text[:8000], api_key)

    if extracted_data:
        # 组装最终符合接口规范的字典
        submission_data = {
            "student_id": student_id,
            "chapter_id": chapter_id,
            "dialogues": extracted_data.get("dialogues", []),
            "final_report": extracted_data.get("final_report", ""),
            "reflection": extracted_data.get("reflection", "")
        }

        save_report(student_id, chapter_id, submission_data)

        print(f"✅ 成功解析学生报告并保存！(提取了 {len(submission_data['dialogues'])} 轮对话)")
        return True
    else:
        print(f"❌ 提取失败: 大模型未能正确解析学生报告。")
        return False