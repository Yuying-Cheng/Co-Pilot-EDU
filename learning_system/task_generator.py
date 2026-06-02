"""
Task generation: extract knowledge points → generate inquiry tasks
"""

import json
from llm_client import call_llm_json, call_llm
from data_store import INTERACTION_TYPES


EXTRACT_SYSTEM = """你是一位算法课程的教学助手，擅长从课程材料中提取核心知识点。
请严格按照要求输出JSON格式，不添加任何解释文字。"""

TASK_GEN_SYSTEM = """你是一位设计探究式学习任务的专家教师。
你的任务是基于知识点，生成符合"多轮交互"要求的探究任务。
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
    """Generate inquiry tasks from knowledge points."""
    kp_summary = json.dumps(knowledge.get("knowledge_points", []),
                            ensure_ascii=False, indent=2)

    prompt = f"""基于以下知识点，生成4-5个探究式学习任务。

章节：{knowledge.get('chapter_title', '')}
知识点：
{kp_summary}

每个任务必须包含：
1. 不同的任务类型（知识整理、算法对比、复杂度分析、苏格拉底引导、批判思考 各选一个）
2. 明确的交互要求（≥10轮、指定至少4种交互方式）
3. 清晰的成果要求

可用的交互方式类型：{', '.join(INTERACTION_TYPES)}

输出JSON格式：
{{
  "course_name": "{knowledge.get('course_name', '')}",
  "chapter_title": "{knowledge.get('chapter_title', '')}",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识整理|算法对比|复杂度分析|苏格拉底引导|批判思考",
      "related_knowledge_points": ["kp001", "kp002"],
      "description": "详细的任务说明（150-250字），包含具体的探究问题和引导方向",
      "interaction_requirements": {{
        "min_rounds": 10,
        "required_types": ["询问", "表达见解", "审辨", "猜想"],
        "must_include_follow_up": true,
        "must_include_questioning": true,
        "guidance": "给学生的交互策略提示（50字以内）"
      }},
      "output_requirements": {{
        "word_limit": "500-800字",
        "need_dialogue_record": true,
        "need_learning_reflection": true,
        "format_hint": "成果格式说明"
      }},
      "editable": true,
      "difficulty": "基础|中等|挑战"
    }}
  ]
}}"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=4000)


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

请生成一个与已有任务不同视角的新任务，格式同前，输出单个task对象的JSON。
包含字段：task_id, title, task_type, related_knowledge_points, description, 
interaction_requirements, output_requirements, editable, difficulty"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=1500)
