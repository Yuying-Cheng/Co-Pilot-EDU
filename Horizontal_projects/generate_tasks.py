import json
from utils.llm_api import call_llm
import re

def load_knowledge(path="data/input/knowledge.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(tasks, path="data/output/task.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)


def build_prompt(knowledge_data):
    return f"""
你是一名课程教学任务设计专家，正在为“大模型驱动的课程探究式学习任务生成与交互质量评价系统”生成课堂探究任务。

请根据下面的 knowledge.json 内容，生成标准的 task.json。

必须严格输出合法 JSON：
1. 不要输出 Markdown。
2. 不要输出 ```json。
3. 不要输出解释文字。
4. 不要在 JSON 前后添加任何多余内容。

输出 JSON 的整体结构必须严格如下：

{{
  "course_name": "课程名称",
  "chapter_id": "章节编号",
  "chapter_title": "章节标题",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识体系整理",
      "related_knowledge_points": ["kp001"],
      "description": "任务描述",
      "interaction_requirements": {{
        "min_rounds": 10,
        "required_types": ["询问", "表达见解", "审辨", "猜想"],
        "must_include_follow_up": true,
        "must_include_questioning": true,
        "need_socratic_dialogue": false
      }},
      "output_requirements": {{
        "word_limit": "500-800字",
        "need_dialogue_record": true,
        "need_learning_reflection": true,
        "required_outputs": ["知识总结", "交互记录", "学习反思"]
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

生成要求：

1. course_name、chapter_id、chapter_title 必须直接来自输入的 knowledge.json，不允许编造。
2. tasks 必须生成 5 个任务。
3. 5 个任务的 task_type 必须分别是：
   - 知识体系整理
   - 算法比较
   - 复杂度分析
   - 批判思考
   - 学习反思
4. 如果课程内容不是算法类课程，可以在 title 和 description 中自然适配课程内容，但 task_type 字段仍必须保持上述五类之一。
5. 每个任务的 related_knowledge_points 只能使用 knowledge.json 中已有的知识点 id，不允许编造新的 kp 编号。
6. 每个任务必须至少关联 1 个知识点，核心任务应优先覆盖 importance 为 core 的知识点。
7. description 必须体现探究式学习特点，不能只是简单问答，必须引导学生比较、分析、追问、解释或反思。
8. interaction_requirements 必须完整包含以下字段：
   - min_rounds: 10
   - required_types: ["询问", "表达见解", "审辨", "猜想"]
   - must_include_follow_up: true
   - must_include_questioning: true
   - need_socratic_dialogue: true 或 false
9. 五个任务中至少有 1 个任务必须是苏格拉底式引导任务，并将 need_socratic_dialogue 设置为 true。
10. 苏格拉底式引导任务的 description 必须体现：
    - AI 连续追问
    - 学生逐步回答
    - 最终由学生自己总结出结论
11. output_requirements 必须是对象，不能是字符串。
12. output_requirements 必须包含：
    - word_limit
    - need_dialogue_record
    - need_learning_reflection
    - required_outputs
13. required_outputs 固定为：
    ["知识总结", "交互记录", "学习反思"]
14. 每个任务必须包含 quality_check 字段。
15. quality_check 固定包含：
    - must_cover_core_knowledge: true
    - must_match_inquiry_learning: true
    - must_match_interaction_requirements: true
16. 每个任务都必须有 editable: true。
17. task_id 按 task001、task002、task003、task004、task005 编号。
18. 最终只输出一个完整合法 JSON 对象。

课程知识点如下：

{json.dumps(knowledge_data, ensure_ascii=False, indent=2)}
"""

def clean_json_text(text):
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()

def main():
    print("开始读取 knowledge.json...")
    knowledge_data = load_knowledge()

    print("开始构造 prompt...")
    prompt = build_prompt(knowledge_data)

    print("开始调用 DeepSeek，请等待...")
    result = call_llm(prompt)

    print("DeepSeek 返回成功，开始解析 JSON...")
    clean_result = clean_json_text(result)
    tasks = json.loads(clean_result)

    save_tasks(tasks)
    print("task.json 已生成：data/output/task.json")


if __name__ == "__main__":
    main()