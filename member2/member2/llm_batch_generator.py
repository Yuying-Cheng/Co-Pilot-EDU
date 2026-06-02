import fitz  # PyMuPDF
import json
import os
import glob
import re
from openai import OpenAI

# ==========================================
# 填入你的 DeepSeek API Key
# ==========================================
client = OpenAI(
    api_key="sk-2cde96e1e2834076b144687dc1a46890",
    base_url="https://api.deepseek.com"
)


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


def call_llm_for_extraction(text: str) -> dict:
    """调用 DeepSeek 进行智能提取"""
    system_prompt = """
    你是一个专业的数据清洗助手。用户会提供一份学生提交的“课程探究任务”作业文本。
    这份文本可能排版极其混乱，包含大量多余换行、错别字或缺失标点。

    你的任务是：
    1. 从中找出该学生的“十问十答”（对话记录）。
    2. 找出该任务的总结（final_report）。
    3. 找出整体反思（reflection）。
    4. 严格以下面的 JSON 格式输出，不要输出任何 Markdown 标记（如 ```json），直接输出合法的 JSON 字符串：

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


def process_single_file(pdf_path: str, output_json: str):
    base_name = os.path.basename(pdf_path).replace('.pdf', '')
    print(f"⏳ 正在处理: {base_name}.pdf ...")

    # 1. 提取文本
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        print(f"⚠️ 警告: {base_name}.pdf 提取不到任何文字，可能是纯图片扫描件！")
        return False

    # 2. 丢给大模型处理 (截取前 8000 字符防止超出 token 限制)
    extracted_data = call_llm_for_extraction(raw_text[:8000])

    if extracted_data:
        # 3. 组装最终符合接口规范的字典
        submission_data = {
            "student_id": f"202301_{base_name}",
            "student_name": f"学生_{base_name}",
            "course_name": "算法设计与分析",
            "chapter_id": "ch04",
            "task_id": "task_01",
            "dialogues": extracted_data.get("dialogues", []),
            "final_report": extracted_data.get("final_report", ""),
            "reflection": extracted_data.get("reflection", "")
        }

        # 4. 保存文件
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(submission_data, f, ensure_ascii=False, indent=4)
        print(f"✅ 成功生成: {base_name}.json (提取了 {len(submission_data['dialogues'])} 轮对话)")
        return True
    else:
        print(f"❌ 提取失败: 大模型未能正确返回 {base_name}.pdf 的数据。")
        return False


def main():
    input_dir = "./pdf_data"
    output_dir = "./json_output"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    print(f"🔍 扫描到 {len(pdf_files)} 个 PDF 文件，启用 AI 强力解析模式...")

    success_count = 0
    for pdf_path in pdf_files:
        output_json = os.path.join(output_dir, os.path.basename(pdf_path).replace('.pdf', '.json'))
        if process_single_file(pdf_path, output_json):
            success_count += 1

    print("=" * 45)
    print(f"🎉 批量 AI 处理完成！成功生成 {success_count}/{len(pdf_files)} 个 JSON 文件。")


if __name__ == "__main__":
    main()