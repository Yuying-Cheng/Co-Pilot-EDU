# -*- coding: utf-8 -*-

import json
import sys
from data.data_manager import load_task, load_knowledge


REQUIRED_TOP_FIELDS = [
    "course_name",
    "chapter_id",
    "chapter_title",
    "tasks"
]

REQUIRED_TASK_FIELDS = [
    "task_id",
    "title",
    "task_type",
    "related_knowledge_points",
    "description",
    "interaction_requirements",
    "output_requirements",
    "quality_check",
    "editable"
]

REQUIRED_TASK_TYPES = [
    "知识体系整理",
    "算法比较",
    "复杂度分析",
    "批判思考",
    "学习反思"
]

REQUIRED_INTERACTION_FIELDS = [
    "min_rounds",
    "required_types",
    "must_include_follow_up",
    "must_include_questioning",
    "need_socratic_dialogue"
]

REQUIRED_OUTPUT_FIELDS = [
    "word_limit",
    "need_dialogue_record",
    "need_learning_reflection",
    "required_outputs"
]

REQUIRED_QUALITY_FIELDS = [
    "must_cover_core_knowledge",
    "must_match_inquiry_learning",
    "must_match_interaction_requirements"
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


def add_error(errors, message):
    errors.append("❌ " + message)


def add_warning(warnings, message):
    warnings.append("⚠️ " + message)


def validate_top_fields(task_data, errors):
    for field in REQUIRED_TOP_FIELDS:
        if field not in task_data:
            add_error(errors, f"顶层缺少字段：{field}")

    if "tasks" in task_data and not isinstance(task_data["tasks"], list):
        add_error(errors, "tasks 必须是列表")


def validate_course_info(task_data, knowledge_data, errors):
    for field in ["course_name", "chapter_id", "chapter_title"]:
        if task_data.get(field) != knowledge_data.get(field):
            add_error(
                errors,
                f"{field} 与 knowledge.json 不一致：task.json={task_data.get(field)}，knowledge.json={knowledge_data.get(field)}"
            )


def validate_task_count(tasks, errors):
    if len(tasks) != 5:
        add_error(errors, f"tasks 数量应为 5，当前为 {len(tasks)}")


def validate_task_types(tasks, errors):
    task_types = [task.get("task_type") for task in tasks]

    for required_type in REQUIRED_TASK_TYPES:
        if required_type not in task_types:
            add_error(errors, f"缺少任务类型：{required_type}")


def validate_related_knowledge_points(tasks, knowledge_data, errors, warnings):
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
            add_error(errors, f"{task_id} 的 related_knowledge_points 必须是非空列表")
            continue

        for kp_id in related:
            used_kp_ids.add(kp_id)
            if kp_id not in all_kp_ids:
                add_error(errors, f"{task_id} 引用了不存在的知识点 id：{kp_id}")

    missing_core = core_kp_ids - used_kp_ids
    if missing_core:
        add_warning(warnings, f"以下核心知识点未被任务覆盖：{sorted(list(missing_core))}")


def validate_interaction_requirements(task, errors):
    task_id = task.get("task_id", "未知任务")
    req = task.get("interaction_requirements")

    if not isinstance(req, dict):
        add_error(errors, f"{task_id} 的 interaction_requirements 必须是对象")
        return

    for field in REQUIRED_INTERACTION_FIELDS:
        if field not in req:
            add_error(errors, f"{task_id} 的 interaction_requirements 缺少字段：{field}")

    if req.get("min_rounds") != 10:
        add_error(errors, f"{task_id} 的 min_rounds 必须为 10")

    if req.get("required_types") != REQUIRED_INTERACTION_TYPES:
        add_error(errors, f"{task_id} 的 required_types 必须为 {REQUIRED_INTERACTION_TYPES}")

    if req.get("must_include_follow_up") is not True:
        add_error(errors, f"{task_id} 的 must_include_follow_up 必须为 true")

    if req.get("must_include_questioning") is not True:
        add_error(errors, f"{task_id} 的 must_include_questioning 必须为 true")

    if not isinstance(req.get("need_socratic_dialogue"), bool):
        add_error(errors, f"{task_id} 的 need_socratic_dialogue 必须为 true 或 false")


def validate_output_requirements(task, errors):
    task_id = task.get("task_id", "未知任务")
    req = task.get("output_requirements")

    if not isinstance(req, dict):
        add_error(errors, f"{task_id} 的 output_requirements 必须是对象")
        return

    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in req:
            add_error(errors, f"{task_id} 的 output_requirements 缺少字段：{field}")

    if req.get("word_limit") != "500-800字":
        add_error(errors, f"{task_id} 的 word_limit 必须为 500-800字")

    if req.get("need_dialogue_record") is not True:
        add_error(errors, f"{task_id} 的 need_dialogue_record 必须为 true")

    if req.get("need_learning_reflection") is not True:
        add_error(errors, f"{task_id} 的 need_learning_reflection 必须为 true")

    if req.get("required_outputs") != REQUIRED_OUTPUTS:
        add_error(errors, f"{task_id} 的 required_outputs 必须为 {REQUIRED_OUTPUTS}")


def validate_quality_check(task, errors):
    task_id = task.get("task_id", "未知任务")
    qc = task.get("quality_check")

    if not isinstance(qc, dict):
        add_error(errors, f"{task_id} 的 quality_check 必须是对象")
        return

    for field in REQUIRED_QUALITY_FIELDS:
        if field not in qc:
            add_error(errors, f"{task_id} 的 quality_check 缺少字段：{field}")

    for field in REQUIRED_QUALITY_FIELDS:
        if qc.get(field) is not True:
            add_error(errors, f"{task_id} 的 quality_check.{field} 必须为 true")


def validate_each_task(tasks, errors, warnings):
    for index, task in enumerate(tasks, start=1):
        task_id = task.get("task_id", f"第{index}个任务")

        for field in REQUIRED_TASK_FIELDS:
            if field not in task:
                add_error(errors, f"{task_id} 缺少字段：{field}")

        expected_task_id = f"task{index:03d}"
        if task.get("task_id") != expected_task_id:
            add_warning(warnings, f"{task_id} 建议编号为 {expected_task_id}")

        if task.get("editable") is not True:
            add_error(errors, f"{task_id} 的 editable 必须为 true")

        description = task.get("description", "")
        if not isinstance(description, str) or len(description) < 30:
            add_warning(warnings, f"{task_id} 的 description 较短，探究性可能不足")

        validate_interaction_requirements(task, errors)
        validate_output_requirements(task, errors)
        validate_quality_check(task, errors)


def validate_socratic_task(tasks, errors):
    count = 0

    for task in tasks:
        req = task.get("interaction_requirements", {})
        if req.get("need_socratic_dialogue") is True:
            count += 1

    if count < 1:
        add_error(errors, "五个任务中至少需要 1 个苏格拉底式引导任务：need_socratic_dialogue=true")


def run_validation(chapter_id: str):
    errors = []
    warnings = []

    try:
        # 使用组长接口读取
        task_data = load_task(chapter_id)
        knowledge_data = load_knowledge(chapter_id)

        if not task_data or not knowledge_data:
            print("❌ 找不到对应的 JSON 文件！")
            return False

    except Exception as e:
        print(f"❌ 读取错误：{e}")
        return False

    validate_top_fields(task_data, errors)

    if errors:
        print("\n".join(errors))
        print("\n检查未通过。")
        sys.exit(1)

    tasks = task_data.get("tasks", [])

    validate_course_info(task_data, knowledge_data, errors)
    validate_task_count(tasks, errors)
    validate_task_types(tasks, errors)
    validate_related_knowledge_points(tasks, knowledge_data, errors, warnings)
    validate_each_task(tasks, errors, warnings)
    validate_socratic_task(tasks, errors)

    print("========== task.json 质量检查结果 ==========")

    if warnings:
        print("\n警告：")
        for warning in warnings:
            print(warning)

    if errors:
        print("\n错误：")
        for error in errors:
            print(error)
        print("\n❌ task.json 检查未通过，请修改后重新生成。")
        sys.exit(1)

    print("✅ task.json 检查通过。")
    print(f"课程名称：{task_data.get('course_name')}")
    print(f"章节：{task_data.get('chapter_id')} - {task_data.get('chapter_title')}")
    print(f"任务数量：{len(tasks)}")
    print("已检查：字段完整性、任务类型、知识点引用、交互要求、成果要求、苏格拉底任务、质量检查字段。")


if __name__ == "__main__":
    main()