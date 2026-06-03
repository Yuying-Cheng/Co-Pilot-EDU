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
你是一名课程教师，正在根据课程知识点设计“课堂探究任务”。

请根据下面的 knowledge.json，生成一个标准 task.json。
注意：输出必须是合法 JSON，不要输出 Markdown，不要输出 ```json，不要输出解释文字。

重要要求：
生成的任务内容要模仿教师课堂任务书风格，不要只生成简短题目。
每个任务都要包含：
1. 明确的任务背景
2. 具体探究步骤
3. 学生需要如何与大模型交互
4. 必须包含的思考点
5. 具体成果要求

输出 JSON 结构必须如下：

{{
  "course_name": "课程名称",
  "chapter_id": "章节编号",
  "chapter_title": "章节标题",
  "task_instruction": "统一任务说明",
  "tasks": [
    {{
      "task_id": "task001",
      "title": "任务标题",
      "task_type": "知识体系整理",
      "related_knowledge_points": ["kp001"],
      "description": "完整任务描述，要求像教师布置课堂探究任务一样详细。",
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
      "editable": true
    }}
  ]
}}

生成要求：
1. course_name、chapter_id、chapter_title 必须来自 knowledge.json。
2. task_instruction 要概括所有任务的统一要求：每个任务需与大模型交互10次以上，每次交互字数不少于50字，至少包含三种不同交互方式，提交完整对话记录和学习心得。
3. tasks 生成 5 个任务。
4. 5 个 task_type 分别为：
   - 知识体系整理
   - 深度理解
   - 对比分析
   - 应用探究
   - 苏格拉底式引导
5. 如果课程是算法类，可自然使用算法比较、复杂度分析；如果课程不是算法类，要根据课程内容适配为协议比较、机制分析、案例分析等，但 task_type 要保持上面五类。
6. 每个任务必须像教师范例一样详细，不允许只写一句话。
7. description 至少 120 字。
8. inquiry_steps 至少 4 步，每一步都要具体可执行。
9. related_knowledge_points 只能使用 knowledge.json 中已有 id。
10. 五个任务要尽量覆盖 importance 为 core 的知识点。
11. 至少一个任务必须是苏格拉底式引导任务，need_socratic_dialogue 必须为 true。
12. 苏格拉底任务必须要求大模型“不要直接给答案，而是通过连续追问引导学生自己推导或总结”。
13. output_requirements.specific_output 必须根据任务内容具体生成，不能所有任务都一样。
14. 最终只输出一个完整合法 JSON 对象。

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