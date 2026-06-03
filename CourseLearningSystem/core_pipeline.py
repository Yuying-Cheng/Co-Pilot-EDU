import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_manager import save_knowledge, save_score, load_knowledge, load_task
from config import DEEPSEEK_API_KEY
from parser.knowledge_engine import KnowledgeEngine
from evaluator.evaluator_v2 import evaluate_submission_v2

from task_generator.generate_tasks import generate_chapter_tasks

def process_course_material(raw_text: str, course_name: str, chapter_id: str, chapter_title: str):
    print(f"🚀 开始处理章节: {chapter_title}")

    # 提取知识点
    try:
        engine = KnowledgeEngine(api_key=DEEPSEEK_API_KEY)
        knowledge_data = engine.generate_knowledge_base(raw_text, course_name, chapter_title)

        if not knowledge_data or (isinstance(knowledge_data, dict) and not knowledge_data.get("knowledge_points")):
            print("❌ 知识点生成失败：模型未返回有效数据，请检查 API 余额！")
            return False

        save_knowledge(chapter_id, knowledge_data)
        print("✅ 知识点提取成功！")
    except Exception as e:
        print(f"❌ 知识点提取失败: {e}")
        return False

    # 基于知识点生成任务
    try:
        success = generate_chapter_tasks(chapter_id)

        if success:
            print("✅ 探究任务生成并保存成功！")
            return True
        else:
            print("❌ 任务生成函数执行失败。")
            return False
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ 任务生成失败: {e}")
        return False

    return True


def evaluate_student(student_id: str, chapter_id: str, dialogue_data: dict):
    """
    接收学生对话 -> 评价打分 -> 保存成绩
    供 UI 界面的【评阅】按钮调用
    """
    print(f"🚀 开始评阅学生 {student_id} 的提交...")

    try:
        # 读取标准任务和知识点作为对照
        task_data = load_task(chapter_id)
        knowledge_data = load_knowledge(chapter_id)

        submission = dict(dialogue_data)
        submission.setdefault("student_id", student_id)
        submission.setdefault("student_name", student_id)
        submission.setdefault("chapter_id", chapter_id)
        if "task_id" not in submission:
            tasks = task_data.get("tasks", [])
            submission["task_id"] = tasks[0].get("task_id", "task001") if tasks else "task001"

        score_result = evaluate_submission_v2(
            knowledge=knowledge_data,
            task_data=task_data,
            submission=submission,
            use_llm=True,
        )
        save_score(student_id, chapter_id, score_result)
        print("✅ 学生评阅完成！")
        return score_result
    except Exception as e:
        print(f"❌ 评阅失败: {e}")
        return False


# ================= 测试入口 =================
if __name__ == "__main__":
    test_text = "这里是一段关于分治法和动态规划的课件测试文本..."
    process_course_material(test_text, "算法分析", "ch01", "分治法基础")

    # 模拟一个学生提交的数据去评阅
    # mock_dialogue = {"dialogues": [{"role": "user", "content": "什么是分治？"}]}
    # evaluate_student("stu_01", "ch01", mock_dialogue)
