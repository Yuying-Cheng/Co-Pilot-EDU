import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    "courses": os.path.join(BASE_DIR, 'courses'),
    "tasks": os.path.join(BASE_DIR, 'tasks'),
    "reports": os.path.join(BASE_DIR, 'reports'),
    "scores": os.path.join(BASE_DIR, 'scores'),
    "analysis": os.path.join(BASE_DIR, 'analysis')
}

for folder in DIRS.values():
    os.makedirs(folder, exist_ok=True)

def _save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def _load_json(filepath):
    if not os.path.exists(filepath):
        print(f"[警告] 文件不存在: {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# ====== 知识点接口 (knowledge) ======
def save_knowledge(chapter_id, knowledge_data):
    filepath = os.path.join(DIRS["courses"], f"{chapter_id}_knowledge.json")
    _save_json(filepath, knowledge_data)

def load_knowledge(chapter_id):
    filepath = os.path.join(DIRS["courses"], f"{chapter_id}_knowledge.json")
    return _load_json(filepath)

# ====== 任务接口 (task) ======
def save_task(chapter_id, task_data):
    filepath = os.path.join(DIRS["tasks"], f"{chapter_id}_task.json")
    _save_json(filepath, task_data)

def load_task(chapter_id):
    filepath = os.path.join(DIRS["tasks"], f"{chapter_id}_task.json")
    return _load_json(filepath)

# ====== 学生提交成果接口 (submission/report) ======
def save_report(student_id, chapter_id, report_data):
    filepath = os.path.join(DIRS["reports"], f"{student_id}_{chapter_id}_report.json")
    _save_json(filepath, report_data)

def load_report(student_id, chapter_id):
    filepath = os.path.join(DIRS["reports"], f"{student_id}_{chapter_id}_report.json")
    return _load_json(filepath)

# ====== 评分接口 (score) ======
def save_score(student_id, chapter_id, score_data):
    filepath = os.path.join(DIRS["scores"], f"{student_id}_{chapter_id}_score.json")
    _save_json(filepath, score_data)

def load_score(student_id, chapter_id):
    filepath = os.path.join(DIRS["scores"], f"{student_id}_{chapter_id}_score.json")
    return _load_json(filepath)

# ====== 学情分析接口 (class_analysis) ======
def save_class_analysis(chapter_id, analysis_data):
    filepath = os.path.join(DIRS["analysis"], f"{chapter_id}_class_analysis.json")
    _save_json(filepath, analysis_data)

def load_class_analysis(chapter_id):
    filepath = os.path.join(DIRS["analysis"], f"{chapter_id}_class_analysis.json")
    return _load_json(filepath)