"""
Task generation: extract knowledge points → generate inquiry tasks.
Prompt style aligned with teacher's sample task sheet.
"""

import json
from llm_client import call_llm_json, call_llm
from data_store import INTERACTION_TYPES


EXTRACT_SYSTEM = """你是一位算法课程的教学助手，擅长从课程材料中提取核心知识点。
请严格按照要求输出JSON格式，不添加任何解释文字。"""

TASK_GEN_SYSTEM = """你是一位设计探究式学习任务的专家教师。
你的任务是基于知识点，生成符合"多轮交互"要求的课堂探究任务。
每个任务必须有具体的探究场景、明确的操作指令、特色交互方式和具体可提交的成果。
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
    """Generate 5 inquiry tasks from knowledge points, aligned with teacher sample style."""
    knowledge_json = json.dumps(knowledge, ensure_ascii=False, indent=2)

    prompt = f"""你是一名课程教师，正在为"探究式学习 + 大模型交互"课堂设计任务书。

请根据下面的知识点数据，生成一个标准 task.json。
输出必须是合法 JSON，不要输出 Markdown，不要输出解释文字。

【风格要求】请严格模仿以下样例的写法，每个任务都要有具体操作场景，不能空泛：

样例任务（仅供风格参考，内容根据实际课程知识点生成）：

样例1——知识体系整理：
  标题：知识点体系整理
  描述：整理本讲的知识体系，与课件比对，判断输出是否完整；若不完整，继续交互补全。
  成果：提交一份完整的知识点体系整理报告。

样例2——深度推导/计算：
  标题：用递归树分析归并排序的时间复杂度
  描述：给定归并排序的递归式 T(n) = 2T(n/2) + cn，通过画递归树、计算每层代价、
  求和推导总复杂度，解释为什么归并排序是 O(n log n)，并尝试推广到3路归并的情况。
  成果：提交递归树手绘图（可手绘拍照）及详细的推导过程。

样例3——角色扮演理解：
  标题：渐近记号深度理解（角色扮演）
  描述：用角色扮演方式，向大模型提问："请扮演一位高中数学老师，用生活化的类比
  和具体数值例子，给刚接触算法的大一学生讲解O、Ω、Θ三种渐近记号的区别。要求：
  先讲直观含义，再给严格定义，最后用同一个函数演示三个记号分别是什么，并解释
  为什么。"通过多轮交互，彻底搞懂这几个容易混淆的概念。
  成果：提交对话记录及你自己的理解总结（用自己的话复述核心区别）。

样例4——对比分析：
  标题：对比 O、Ω、Θ 三种渐近记号的异同
  描述：通过具体函数例子，说明其 O、Ω、Θ 分别是什么，并解释为什么。
  设计一个容易混淆的判断题（如"n²=O(n³)对吗？n³=O(n²)对吗？"），
  通过反例帮助理解这些记号的严格定义。
  成果：提交对比分析报告，包含定义解释、函数例子分析、自设计判断题及解析。

样例5——苏格拉底式引导：
  标题：递归树分析（苏格拉底式导师）
  描述：向大模型提问："请你扮演苏格拉底式导师，不要直接告诉我答案，只通过
  一步步提问引导我自己推导出归并排序的时间复杂度。我从递归式T(n)=2T(n/2)+cn
  开始，你通过提问引导我画出递归树、计算每层代价、求和得到总复杂度。"
  按照模型的引导一步步完成推导。
  成果：提交对话记录及你最终推导出的递归树和复杂度结果。

【生成要求】
1. course_name、chapter_id、chapter_title 必须直接来自输入的知识点数据。
2. 生成恰好 5 个任务，task_type 依次为：
   知识体系整理、深度推导、角色扮演理解、对比分析、苏格拉底式引导。
3. description 必须包含具体的操作指令，不能只写"请整理知识点"这种空话。
   - 深度推导类：给出具体公式、数据或推导起点
   - 角色扮演类：给出完整的角色设定提问模板（用引号括起来）
   - 苏格拉底类：给出完整的苏格拉底导师提问模板（用引号括起来），
     且必须明确要求大模型"不要直接告诉我答案，只通过提问引导"
   - 对比分析类：给出具体的对比维度和自设计题目的要求
4. specific_output（成果要求）必须具体，不同任务要有所区别，例如：
   - 知识体系整理：提交完整知识点体系整理报告
   - 深度推导：提交手绘推导图（可拍照）及详细推导过程
   - 角色扮演：提交对话记录及用自己的话写的理解总结
   - 对比分析：提交对比分析报告，包含自设计判断题及解析
   - 苏格拉底：提交对话记录及最终推导结果
5. 苏格拉底式任务的 need_socratic_dialogue 必须为 true。
6. related_knowledge_points 只能使用输入数据中已有的知识点 id。
7. 五个任务要尽量覆盖 importance 为 core 的知识点。
8. task_instruction 固定使用下面这段文字，不要修改：
   "每个任务需与大模型交互15次以上，每次交互字数不少于50字，且交互过程中必须
   至少包含三种不同的交互方式（如：询问、表达见解、审辨、猜想、想象、创新、
   回答苏格拉底式提问等）。提交完整对话记录，并根据任务要求提交相应成果，
   附个人学习心得。"

输出 JSON 结构如下（最终只输出一个完整合法的 JSON 对象）：
{{
  "course_name": "课程名称",
  "chapter_id": "章节编号",
  "chapter_title": "章节标题",
  "task_instruction": "每个任务需与大模型交互15次以上……（见上方固定文本）",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识体系整理",
      "difficulty": "基础|中等|挑战",
      "related_knowledge_points": ["kp001"],
      "description": "具体操作场景描述，包含明确指令或完整提问模板（不少于80字）",
      "interaction_requirements": {{
        "min_rounds": 15,
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
        "required_outputs": ["探究报告", "交互记录", "学习反思"],
        "specific_output": "具体成果描述，如手绘图、自设计题目、用自己话复述等"
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

课程知识点如下：
{knowledge_json}"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=5000)


def regenerate_single_task(knowledge: dict, task_type: str, existing_tasks: list) -> dict:
    """Regenerate one task of a specific type."""
    existing_titles = [t.get("title", "") for t in existing_tasks]
    kp_summary = json.dumps(
        knowledge.get("knowledge_points", [])[:5],
        ensure_ascii=False,
        indent=2
    )

    type_hints = {
        "知识体系整理": "要求学生整理完整知识体系，与课件比对补全",
        "深度推导": "给出具体公式或推导起点，要求手绘图或详细推导过程",
        "角色扮演理解": "给出完整的角色设定提问模板（用引号括起来）",
        "对比分析": "给出具体对比维度，要求自设计判断题及解析",
        "苏格拉底式引导": (
            "给出完整的苏格拉底导师提问模板，明确要求大模型不直接给答案，"
            "need_socratic_dialogue 必须为 true"
        ),
    }
    hint = type_hints.get(task_type, "任务描述需具体，包含明确操作指令")

    prompt = f"""基于以下知识点，重新生成一个【{task_type}】类型的探究任务。

章节：{knowledge.get('chapter_title', '')}
知识点（部分）：
{kp_summary}

已有任务标题（避免重复）：{existing_titles}

任务类型提示：{hint}

请生成一个与已有任务不同视角的新任务，包含以下所有字段：
task_id（自动编号）、title、task_type（固定为"{task_type}"）、
difficulty、related_knowledge_points、description（≥80字，包含具体指令或模板）、
interaction_requirements（min_rounds=15）、output_requirements
（specific_output要具体）、quality_check、editable。

输出单个 task 对象的 JSON，不要包含其他内容。"""

    return call_llm_json(TASK_GEN_SYSTEM, prompt, max_tokens=1500)
