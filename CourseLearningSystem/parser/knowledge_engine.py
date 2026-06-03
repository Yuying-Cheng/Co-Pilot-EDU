import json
import re
import sys  # <--- 新增这行
from openai import OpenAI

# <--- 新增下面这两行，强制控制台使用 UTF-8 编码打印
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class KnowledgeEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def generate_knowledge_base(self, raw_text: str, course_name: str, chapter_title: str) -> dict:
        """
        第二周任务 1/2/3：从任意长文本中提取知识点，建立层级树、重要度区分与摘要生成
        """
        print(f"🧠 正在分析课件《{chapter_title}》，构建知识体系层级树...")

        system_prompt = """
        你是一个严谨的计算机算法课程助教。请阅读用户提供的课件文本，提取核心知识体系。

        【第二周 核心要求】
        1. 知识点层级必须分明：要涵盖 concept(核心概念), algorithm(重点算法), difficulty(难点/易错点), application(应用延伸)。
        2. 必须明确区分重要度：core(核心重点，必考), important(重要), extended(扩展了解)。
        3. 必须生成一段精炼的 summary 摘要，概括本章重点掌握的核心脉络。

        请严格以下列 JSON 格式输出，不要包含任何 Markdown 标记：
        {
          "course_name": "课程名称",
          "chapter_id": "自动生成如 ch01",
          "chapter_title": "章节标题",
          "summary": "例如：本章重点掌握：1. 分治思想 2. 递归结构 3. 时间复杂度分析...",
          "knowledge_points": [
            {
              "id": "kp001",
              "name": "知识点名称",
              "type": "concept | algorithm | difficulty | application",
              "importance": "core | important | extended",
              "description": "详细说明"
            }
          ]
        }
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",
                     "content": f"课程名称：{course_name}\n章节：{chapter_title}\n课件内容：\n{raw_text[:8000]}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            result_str = response.choices[0].message.content
            result_str = re.sub(r'^```json\s*', '', result_str)
            result_str = re.sub(r'\s*```$', '', result_str)
            return json.loads(result_str)

        except Exception as e:
            print(f"❌ 知识点提取失败: {e}")
            return {}

    def extract_student_text(self, submission_data: dict) -> str:
        """辅助方法：合并学生的所有交互历史"""
        texts = []
        for d in submission_data.get("dialogues", []):
            if "student_input" in d:
                texts.append(f"【学生发言】: {d['student_input']}")
        if "final_report" in submission_data:
            texts.append(f"【最终报告】: {submission_data['final_report']}")
        if "reflection" in submission_data:
            texts.append(f"【学习反思】: {submission_data['reflection']}")
        return "\n".join(texts)

    def calculate_coverage(self, knowledge_points: list, submission_data: dict) -> dict:
        """
        知识覆盖检测算法。
        """
        student_text = self.extract_student_text(submission_data)

        # 精简传输给大模型的字典，避免 token 浪费
        kp_simplified = [{"id": kp["id"], "name": kp["name"]} for kp in knowledge_points]

        system_prompt = """
        你是一个严谨的 AI 助教。任务是对比【学生输出】和【知识点库】。
        必须对知识点库中的 *每一个* 知识点进行逐一排查。

        【判断标准】
        1. covered (掌握)：学生准确表达了该知识点，或进行了有效的质疑、猜想。
        2. missing (遗漏)：学生完全没有提及。
        3. weak (薄弱)：学生提到了，但理解存在明显偏差、或者表述极度肤浅。

        请严格输出以下 JSON 格式：
        {
            "analysis_details": [
                {
                    "id": "kp001",
                    "name": "知识点名称",
                    "evidence": "提取学生原文作为证据。完全没提到写'未提及'。",
                    "status": "covered | missing | weak"
                }
            ]
        }
        """

        user_content = f"【知识点库】:\n{json.dumps(kp_simplified, ensure_ascii=False)}\n\n【学生输出】:\n{student_text}"

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            result_str = re.sub(r'^```json\s*|\s*```$', '', response.choices[0].message.content)
            analysis_result = json.loads(result_str)

            # 【核心逻辑】： covered 和 missing 用 ID，weak 用名称（name）
            final_output = {
                "covered_points": [],
                "missing_points": [],
                "weak_points": []
            }

            for item in analysis_result.get("analysis_details", []):
                kp_id = item["id"]
                kp_name = item.get("name", kp_id)  # 提取大模型返回的知识点名称

                if item["status"] == "covered":
                    final_output["covered_points"].append(kp_id)
                elif item["status"] == "missing":
                    final_output["missing_points"].append(kp_id)
                elif item["status"] == "weak":
                    final_output["weak_points"].append(kp_name)  # 写入纯文字名称

            return final_output

        except Exception as e:
            print(f"❌ 覆盖检测失败: {e}")
            return {"covered_points": [], "missing_points": [], "weak_points": []}


if __name__ == "__main__":
    engine = KnowledgeEngine(api_key="sk-你的真实APIKey")

    sample_raw_text = "分治法的核心是将复杂问题拆解为独立子问题，经典算法包括归并排序..."

    knowledge_base = engine.generate_knowledge_base(
        raw_text=sample_raw_text,
        course_name="算法设计与分析",
        chapter_title="分治法"
    )

    sample_student_submission = {
        "dialogues": [{"student_input": "我认为归并排序就是把数组一分为二，这体现了分治法。"}],
        "final_report": "我掌握了拆分，但不清楚怎么合并。"
    }

    if "knowledge_points" in knowledge_base:
        coverage = engine.calculate_coverage(knowledge_base["knowledge_points"], sample_student_submission)
        print("\n📊 覆盖分析接口数据:")
        print(json.dumps(coverage, indent=2, ensure_ascii=False))