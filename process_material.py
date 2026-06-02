import os
import json
import sys
from knowledge_engine import KnowledgeEngine

# 引入你第一周写好的解析器
from parser import extract_text

# 解决 Windows 终端中文乱码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def process_uploaded_file(filepath: str, course_name: str, api_key: str, output_dir: str = "./knowledge_bases"):
    """
    处理任意上传的课件，提取文本并按原文件名动态生成专属 JSON
    这个函数专供前端 GUI 或系统主控模块调用。
    """
    # 1. 提取纯文件名
    base_name = os.path.basename(filepath)
    file_name_without_ext = os.path.splitext(base_name)[0]

    print(f"📂 接收到新上传文件: {base_name}，准备解析...")

    # 2. 提取纯文本
    try:
        raw_text = extract_text(filepath)
        if not raw_text:
            print(f"⚠️ 警告: 从 {base_name} 中提取到的文本为空。")
            return None
    except Exception as e:
        print(f"❌ 解析文件失败: {e}")
        return None

    # 3. 启动大模型知识引擎进行分析
    print(f"🧠 正在为《{file_name_without_ext}》抽取知识层级树...")
    engine = KnowledgeEngine(api_key=api_key)

    knowledge_data = engine.generate_knowledge_base(
        raw_text=raw_text,
        course_name=course_name,
        chapter_title=file_name_without_ext
    )

    # 4. 动态命名并保存 JSON 文件
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_filename = f"knowledge_{file_name_without_ext}.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_data, f, ensure_ascii=False, indent=4)

    print(f"✅ 成功！专属知识库已保存至 -> {output_path}")

    # 将生成的文件路径返回给调用方，方便后续流转
    return output_path