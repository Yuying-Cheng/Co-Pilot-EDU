# -*- coding: utf-8 -*-

import json
import sys


TASK_JSON_PATH = "data/output/task.json"
KNOWLEDGE_JSON_PATH = "data/input/knowledge.json"

REQUIRED_TOP_FIELDS = [
    "course_name",
    "chapter_id",
    "chapter_title",
    "task_instruction",
    "tasks"
]

REQUIRED_TASK_FIELDS = [
    "task_id",
    "title",
    "task_type",
    "related_knowledge_points",
    "description",
    "inquiry_steps",
    "interaction_requirements",
    "output_requirements",
    "quality_check",
    "editable"
]

REQUIRED_TASK_TYPES = [
    "知识体系整理",
    "深度理解",
    "对比分析",
    "应用探究",
    "苏格拉底式引导"
]

REQUIRED_INTERACTION_TYPES = [
    "询问",
    "表达见解",
    "审辨",
    "猜想"
]

REQUIRED_OUTPUTS = [
    "知识总结",
    "交互记录",
    "学习反思"
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_error(errors, msg):
    errors.append("❌ " + msg)


def add_warning(warnings, msg):
    warnings.append("⚠️ " + msg)


def validate_top(task_data, knowledge_data, errors):
    for field in REQUIRED_TOP_FIELDS:
        if field not in task_data:
            add_error(errors, f"顶层缺少字段：{field}")

    if task_data.get("course_name") != knowledge_data.get("course_name"):
        add_error(errors, "course_name 与 knowledge.json 不一致")

    if task_data.get("chapter_id") != knowledge_data.get("chapter_id"):
        add_error(errors, "chapter_id 与 knowledge.json 不一致")

    if task_data.get("chapter_title") != knowledge_data.get("chapter_title"):
        add_error(errors, "chapter_title 与 knowledge.json 不一致")

    if not isinstance(task_data.get("task_instruction"), str) or len(task_data.get("task_instruction", "")) < 30:
        add_error(errors, "task_instruction 太短或不是字符串")

    if not isinstance(task_data.get("tasks"), list):
        add_error(errors, "tasks 必须是列表")


def validate_task_count(tasks, errors):
    if len(tasks) != 5:
        add_error(errors, f"tasks 数量应为 5，当前为 {len(tasks)}")


def validate_task_types(tasks, errors):
    task_types = [task.get("task_type") for task in tasks]

    for task_type in REQUIRED_TASK_TYPES:
        if task_type not in task_types:
            add_error(errors, f"缺少任务类型：{task_type}")


def validate_related_knowledge(tasks, knowledge_data, errors, warnings):
    all_kp_ids = {
        kp["id"]
        for kp in knowledge_data.get("knowledge_points", [])
        if "id" in kp
    }

    core_kp_ids = {
        kp["id"]
        for kp in knowledge_data.get("knowledge_points", [])
        if kp.get("importance") == "core"
    }

    used_kp_ids = set()

    for task in tasks:
        task_id = task.get("task_id", "未知任务")
        related = task.get("related_knowledge_points")

        if not isinstance(related, list) or len(related) == 0:
            add_error(errors, f"{task_id} related_knowledge_points 必须是非空列表")
            continue

        for kp_id in related:
            used_kp_ids.add(kp_id)
            if kp_id not in all_kp_ids:
                add_error(errors, f"{task_id} 引用了不存在的知识点：{kp_id}")

    missing_core = core_kp_ids - used_kp_ids
    if missing_core:
        add_warning(warnings, f"以下核心知识点未被任务覆盖：{sorted(list(missing_core))}")


def validate_interaction(task, errors):
    task_id = task.get("task_id", "未知任务")
    req = task.get("interaction_requirements")

    if not isinstance(req, dict):
        add_error(errors, f"{task_id} interaction_requirements 必须是对象")
        return

    required_fields = [
        "min_rounds",
        "min_words_per_round",
        "required_types",
        "must_include_follow_up",
        "must_include_questioning",
        "need_socratic_dialogue"
    ]

    for field in required_fields:
        if field not in req:
            add_error(errors, f"{task_id} interaction_requirements 缺少字段：{field}")

    if req.get("min_rounds") != 10:
        add_error(errors, f"{task_id} min_rounds 必须为 10")

    if req.get("min_words_per_round") != 50:
        add_error(errors, f"{task_id} min_words_per_round 必须为 50")

    required_types = req.get("required_types")
    if not isinstance(required_types, list):
        add_error(errors, f"{task_id} required_types 必须是列表")
    else:
        for t in REQUIRED_INTERACTION_TYPES:
            if t not in required_types:
                add_error(errors, f"{task_id} required_types 缺少：{t}")

    if req.get("must_include_follow_up") is not True:
        add_error(errors, f"{task_id} must_include_follow_up 必须为 true")

    if req.get("must_include_questioning") is not True:
        add_error(errors, f"{task_id} must_include_questioning 必须为 true")

    if not isinstance(req.get("need_socratic_dialogue"), bool):
        add_error(errors, f"{task_id} need_socratic_dialogue 必须是 true 或 false")


def validate_output(task, errors):
    task_id = task.get("task_id", "未知任务")
    req = task.get("output_requirements")

    if not isinstance(req, dict):
        add_error(errors, f"{task_id} output_requirements 必须是对象")
        return

    required_fields = [
        "word_limit",
        "need_dialogue_record",
        "need_learning_reflection",
        "reflection_min_words",
        "required_outputs",
        "specific_output"
    ]

    for field in required_fields:
        if field not in req:
            add_error(errors, f"{task_id} output_requirements 缺少字段：{field}")

    if req.get("need_dialogue_record") is not True:
        add_error(errors, f"{task_id} need_dialogue_record 必须为 true")

    if req.get("need_learning_reflection") is not True:
        add_error(errors, f"{task_id} need_learning_reflection 必须为 true")

    if req.get("reflection_min_words") not in [100, 150]:
        add_warning(errors, f"{task_id} reflection_min_words 建议为 100 或 150")

    outputs = req.get("required_outputs")
    if not isinstance(outputs, list):
        add_error(errors, f"{task_id} required_outputs 必须是列表")
    else:
        for item in REQUIRED_OUTPUTS:
            if item not in outputs:
                add_error(errors, f"{task_id} required_outputs 缺少：{item}")

    if not isinstance(req.get("specific_output"), str) or len(req.get("specific_output", "")) < 20:
        add_error(errors, f"{task_id} specific_output 太短")


def validate_quality(task, errors):
    task_id = task.get("task_id", "未知任务")
    qc = task.get("quality_check")

    if not isinstance(qc, dict):
        add_error(errors, f"{task_id} quality_check 必须是对象")
        return

    fields = [
        "must_cover_core_knowledge",
        "must_match_inquiry_learning",
        "must_match_interaction_requirements"
    ]

    for field in fields:
        if qc.get(field) is not True:
            add_error(errors, f"{task_id} quality_check.{field} 必须为 true")


def validate_each_task(tasks, errors, warnings):
    for index, task in enumerate(tasks, start=1):
        task_id = task.get("task_id", f"第{index}个任务")

        for field in REQUIRED_TASK_FIELDS:
            if field not in task:
                add_error(errors, f"{task_id} 缺少字段：{field}")

        expected_task_id = f"task{index:03d}"
        if task.get("task_id") != expected_task_id:
            add_warning(warnings, f"{task_id} 建议编号为 {expected_task_id}")

        if not isinstance(task.get("title"), str) or len(task.get("title", "")) < 5:
            add_error(errors, f"{task_id} title 太短")

        if not isinstance(task.get("description"), str) or len(task.get("description", "")) < 120:
            add_warning(warnings, f"{task_id} description 建议不少于 120 字，更接近教师范例风格")

        steps = task.get("inquiry_steps")
        if not isinstance(steps, list) or len(steps) < 4:
            add_error(errors, f"{task_id} inquiry_steps 至少需要 4 步")
        else:
            for i, step in enumerate(steps, start=1):
                if not isinstance(step, str) or len(step) < 10:
                    add_warning(warnings, f"{task_id} 第 {i} 个 inquiry_step 较短")

        if task.get("editable") is not True:
            add_error(errors, f"{task_id} editable 必须为 true")

        validate_interaction(task, errors)
        validate_output(task, errors)
        validate_quality(task, errors)


def validate_socratic(tasks, errors):
    count = 0
    for task in tasks:
        req = task.get("interaction_requirements", {})
        if req.get("need_socratic_dialogue") is True:
            count += 1

            text = task.get("description", "") + " ".join(task.get("inquiry_steps", []))
            if "不要直接" not in text and "引导" not in text and "追问" not in text:
                add_warning(errors, f"{task.get('task_id')} 标记为苏格拉底任务，但描述中没有明显体现引导式追问")

    if count < 1:
        add_error(errors, "至少需要 1 个苏格拉底式引导任务")


def main():
    errors = []
    warnings = []

    try:
        task_data = load_json(TASK_JSON_PATH)
        knowledge_data = load_json(KNOWLEDGE_JSON_PATH)
    except FileNotFoundError as e:
        print(f"❌ 文件不存在：{e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误：{e}")
        sys.exit(1)

    validate_top(task_data, knowledge_data, errors)

    if errors:
        print("========== task.json 质量检查结果 ==========")
        for error in errors:
            print(error)
        sys.exit(1)

    tasks = task_data["tasks"]

    validate_task_count(tasks, errors)
    validate_task_types(tasks, errors)
    validate_related_knowledge(tasks, knowledge_data, errors, warnings)
    validate_each_task(tasks, errors, warnings)
    validate_socratic(tasks, errors)

    print("========== task.json 质量检查结果 ==========")

    if warnings:
        print("\n警告：")
        for warning in warnings:
            print(warning)

    if errors:
        print("\n错误：")
        for error in errors:
            print(error)
        print("\n❌ task.json 检查未通过。")
        sys.exit(1)

    print("✅ task.json 检查通过。")
    print(f"课程名称：{task_data.get('course_name')}")
    print(f"章节：{task_data.get('chapter_id')} - {task_data.get('chapter_title')}")
    print(f"任务数量：{len(tasks)}")
    print("已检查：任务说明、字段完整性、任务类型、探究步骤、交互要求、成果要求、苏格拉底任务、质量检查字段。")


if __name__ == "__main__":
    main()