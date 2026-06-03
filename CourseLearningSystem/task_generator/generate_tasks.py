import json
import re

from data.data_manager import load_knowledge, save_task
from task_generator.utils.llm_api import call_llm


def build_prompt(knowledge_data):
    return f"""
你是一名算法课程教师，正在为“探究式学习 + 大模型交互”课堂生成可直接布置给学生的课堂探究任务。

请根据给定 knowledge.json 生成 task.json。输出必须是合法 JSON，不要 Markdown，不要解释文字。

整体要求：
1. 任务面向教师课堂使用，不是普通习题，也不是简单问答。
2. 任务风格参考“算法基础/贪心法/回溯法课堂探究任务”：先有总任务说明，再有 3-6 个完整探究任务。
3. 每个任务必须引导学生通过多轮大模型交互逐步形成成果，强调过程质量，而不是直接让模型给答案。
4. 每个任务必须包含：任务标题、任务类型、任务描述、需要探究的问题、提示、交互要求、成果要求、质量检查。
5. 交互要求默认不少于 10 轮；如果任务复杂可设置 15 轮。每轮交互建议不少于 50 字。
6. 每个任务至少要求 3 种交互方式；重点任务应包含“询问、表达见解、审辨、猜想”。
7. 至少生成 1 个苏格拉底式引导任务，need_socratic_dialogue=true。
8. 成果要求必须具体可提交，例如：知识体系整理报告、对比分析表、推导过程、手动模拟记录、交互记录、学习反思。
9. 如果课程内容是算法类，任务应优先包含知识体系整理、算法对比、复杂度分析、典型案例推演、审辨/创新、大模型应用迁移等。

JSON 结构如下：
{{
  "course_name": "课程名称",
  "chapter_id": "章节编号",
  "chapter_title": "章节标题",
  "task_sheet_intro": "任务说明：每个任务需与大模型交互10次以上……",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识体系整理 | 算法对比 | 复杂度分析 | 案例推演 | 苏格拉底引导 | 审辨创新 | 学习反思",
      "difficulty": "基础 | 中等 | 挑战",
      "related_knowledge_points": ["kp001"],
      "description": "面向学生的完整任务描述，像课堂任务书一样自然、具体、可执行。",
      "inquiry_points": [
        "学生需要探究的问题1",
        "学生需要探究的问题2"
      ],
      "hints": [
        "提示学生如何与大模型展开多轮交互",
        "提示学生先表达自己的理解，再要求模型评判或追问"
      ],
      "interaction_requirements": {{
        "min_rounds": 10,
        "min_words_per_round": 50,
        "required_types": ["询问", "表达见解", "审辨", "猜想"],
        "must_include_follow_up": true,
        "must_include_questioning": true,
        "need_socratic_dialogue": false
      }},
      "output_requirements": {{
        "word_limit": "500-800字",
        "need_dialogue_record": true,
        "need_learning_reflection": true,
        "reflection_min_words": 150,
        "required_outputs": ["探究报告", "交互记录", "学习反思"]
      }},
      "quality_check": {{
        "must_cover_core_knowledge": true,
        "must_match_inquiry_learning": true,
        "must_match_interaction_requirements": true
      }},
      "editable": true
    }}
  ]
}}

约束：
- course_name、chapter_id、chapter_title 必须直接来自输入 knowledge.json。
- related_knowledge_points 只能使用输入中已有知识点 id。
- 至少 3 个任务，最多 6 个任务。
- 不要生成标准答案。
- 不要只写“请总结知识点”这种空泛描述，必须写清楚探究维度和成果要求。

输入 knowledge.json：
{json.dumps(knowledge_data, ensure_ascii=False, indent=2)}
"""


def clean_json_text(text):
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def generate_chapter_tasks(chapter_id: str) -> bool:
    print(f"开始为章节 {chapter_id} 生成课堂探究任务...")
    knowledge_data = load_knowledge(chapter_id)
    if not knowledge_data:
        print(f"找不到章节 {chapter_id} 的知识点，请先导入课程材料。")
        return False

    try:
        response_text = call_llm(build_prompt(knowledge_data))
        task_data = json.loads(clean_json_text(response_text))
        save_task(chapter_id, task_data)
        print(f"章节 {chapter_id} 的课堂探究任务已生成并保存。")
        return True
    except Exception as e:
        print(f"任务生成失败: {e}")
        return False


if __name__ == "__main__":
    generate_chapter_tasks("ch_未命名章节")
