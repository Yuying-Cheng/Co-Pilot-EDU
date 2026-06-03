"""
Task generation: extract knowledge points → generate inquiry tasks.
Uses the detailed prompt from Horizontal_projects for richer task structure.
"""

import json
from llm_client import call_llm_json, call_llm
from data_store import INTERACTION_TYPES


EXTRACT_SYSTEM = """你是一位算法课程的教学助手，擅长从课程材料中提取核心知识点。
请严格按照要求输出JSON格式，不添加任何解释文字。"""

TASK_GEN_SYSTEM = """你是一位设计探究式学习任务的专家教师。
你的任务是基于知识点，生成符合"多轮交互"要求的探究任务，模仿教师课堂任务书风格。
每个任务必须要求学生与大模型进行≥10轮有效交互，且交互要有深度、有追问、有质疑。
严格按照要求输出JSON格式，不添加任何解释文字。"""


def extract_knowledge(raw_text: str, chapter_title: str = "") -> dict:
    """Extract knowledge points from course material text."""
    prompt = f"""请从以下课程材料中提取核心知识点，生成结构化的知识点列表。

课程材料：
{raw_text}

请输出如下JSON格式：
{{
  "course_name": "课程名称（从材料中推断）",
  "chapter_title": "{chapter_title or '从材料中推断章节标题'}",
  "summary": "本章内容摘要（100字以内）",
  "knowledge_points": [
    {{
      "id": "kp001",
      "name": "知识点名称",
      "type": "concept|algorithm|difficulty|application",
      "importance": "core|important|extended",
      "description": "知识点详细说明（50-100字）"
    }}
  ]
}}

要求：
1. 提取5-12个知识点
2. 覆盖概念、算法、难点、应用等不同类型
3. 按重要性排序，核心知识点放前面
4. description要具体，不要空洞"""

    return call_llm_json(EXTRACT_SYSTEM, prompt, max_tokens=3000)


def generate_tasks(knowledge: dict) -> dict:
    """Generate 5 detailed inquiry tasks from knowledge points (Horizontal_projects style)."""
    knowledge_json = json.dumps(knowledge, ensure_ascii=False, indent=2)

    prompt = f"""你是一名课程教师，正在根据课程知识点设计"课堂探究任务"。

请根据下面的知识点数据，生成一个标准 task.json。
注意：输出必须是合法 JSON，不要输出 Markdown，不要输出解释文字。

重要要求：生成的任务内容要模仿教师课堂任务书风格，不要只生成简短题目。
每个任务都要包含：明确任务背景、具体探究步骤、学生如何与大模型交互、必须包含的思考点、具体成果要求。

输出 JSON 结构必须如下：

{{
  "course_name": "课程名称",
  "chapter_id": "章节编号",
  "chapter_title": "章节标题",
  "task_instruction": "统一任务说明：每个任务需与大模型交互10次以上，每次交互字数不少于50字，至少包含三种不同交互方式，提交完整对话记录和学习心得。",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识体系整理",
      "related_knowledge_points": ["kp001"],
      "description": "完整任务描述，要求像教师布置课堂探究任务一样详细（至少120字）。",
      "inquiry_steps": [
        "步骤1：向大模型询问相关概念的基本含义。",
        "步骤2：表达自己对该知识点的理解，请模型评判并补充。",
        "步骤3：结合具体例子继续追问。",
        "步骤4：提出质疑或批判性问题，形成自己的判断。"
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
        "reflection_min_words": 100,
        "required_outputs": ["知识总结", "交互记录", "学习反思"],
        "specific_output": "提交一份完整的探究报告，包含知识点总结、探究过程、个人理解和反思。"
      }},
      "quality_check": {{
        "must_cover_core_knowledge": true,
        "must_match_inquiry_learning": true,
        "must_match_interaction_requirements": true
      }},
      "editable": true,
      "difficulty": "基础|中等|挑战"
    }}
  ]
}}

生成要求：
1. course_name、chapter_id、chapter_title 必须来自知识点数据。
2. tasks 生成 5 个任务，task_type 分别为：知识体系整理、深度理解、对比分析、应用探究、苏格拉底式引导。
3. 如果课程是算法类，可自然使用算法比较、复杂度分析；否则根据课程内容适配，但 task_type 保持上面五类。
4. description 至少 120 字。
5. inquiry_steps 至少 4 步，每一步都要具体可执行。
6. related_knowledge_points 只能使用知识点数据中已有的 id。
7. 五个任务要尽量覆盖 importance 为 core 的知识点。
8. 苏格拉底式引导任务的 need_socratic_dialogue 必须为 true，且 description 中必须要求大模型"不要直接给答案，而是通过连续追问引导学生自己推导或总结"。
9. output_requirements.specific_output 必须根据任务内容具体生成，不能所有任务都一样。
10. 最终只输出一个完整合法 JSON 对象。

课程知识点如下：

{knowledge_json}"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=5000)


def regenerate_single_task(knowledge: dict, task_type: str, existing_tasks: list) -> dict:
    """Regenerate one task of a specific type."""
    existing_titles = [t.get("title", "") for t in existing_tasks]
    kp_summary = json.dumps(knowledge.get("knowledge_points", [])[:5],
                            ensure_ascii=False, indent=2)

    prompt = f"""基于以下知识点，重新生成一个【{task_type}】类型的探究任务。

章节：{knowledge.get('chapter_title', '')}
知识点（部分）：
{kp_summary}

已有任务标题（避免重复）：{existing_titles}

请生成一个与已有任务不同视角的新任务，包含字段：
task_id, title, task_type, related_knowledge_points, description（≥120字）,
inquiry_steps（≥4步）, interaction_requirements, output_requirements, quality_check, editable, difficulty。

如果是苏格拉底式引导任务，need_socratic_dialogue 必须为 true。
输出单个 task 对象的 JSON。"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=1500)