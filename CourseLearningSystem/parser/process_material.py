import os
import sys

from parser.knowledge_engine import KnowledgeEngine
from parser.parser import extract_text

from data.data_manager import save_knowledge

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def process_uploaded_file(filepath: str, course_name: str, chapter_id: str, api_key: str):
    """
    提取课件 -> 调用大模型 -> 使用组长接口保存
    """
    base_name = os.path.basename(filepath)
    chapter_title = os.path.splitext(base_name)[0]

    print(f"📂 接收到新上传文件: {base_name}，准备解析...")

    try:
        # 调用 parser.py 里的统一入口
        raw_text = extract_text(filepath)
        if not raw_text:
            print(f"⚠️ 警告: 从 {base_name} 中提取到的文本为空。")
            return False
    except Exception as e:
        print(f"❌ 解析文件失败: {e}")
        return False

    print(f"🧠 正在为《{chapter_title}》抽取知识层级树...")
    engine = KnowledgeEngine(api_key=api_key)

    # 生成知识点字典
    knowledge_data = engine.generate_knowledge_base(
        raw_text=raw_text,
        course_name=course_name,
        chapter_title=chapter_title
    )

    if knowledge_data:
        knowledge_data['chapter_id'] = chapter_id
        save_knowledge(chapter_id, knowledge_data)
        print(f"✅ 知识点已保存到 data/courses/{chapter_id}_knowledge.json！")
        return True

    return False