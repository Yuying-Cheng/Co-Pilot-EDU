# -*- coding: utf-8 -*-

TASK_TYPES = [
    "知识体系整理",
    "算法比较",
    "复杂度分析",
    "批判思考",
    "学习反思"
]

INTERACTION_TYPES = [
    "询问",
    "表达见解",
    "审辨",
    "猜想"
]

DEFAULT_INTERACTION_REQUIREMENTS = {
    "min_rounds": 10,
    "required_types": INTERACTION_TYPES,
    "must_include_follow_up": True,
    "must_include_questioning": True,
    "need_socratic_dialogue": False
}

DEFAULT_OUTPUT_REQUIREMENTS = {
    "word_limit": "500-800字",
    "need_dialogue_record": True,
    "need_learning_reflection": True,
    "required_outputs": [
        "知识总结",
        "交互记录",
        "学习反思"
    ]
}

TASK_TEMPLATE_DESCRIPTIONS = {
    "知识体系整理": "引导学生围绕核心知识点建立完整知识框架，梳理概念、关系、流程和适用场景。",
    "算法比较": "引导学生对两个或多个算法、协议、机制进行对比，分析其原理、优缺点和适用条件。",
    "复杂度分析": "引导学生分析算法、协议或机制的时间成本、空间成本、通信开销或实现代价。",
    "批判思考": "引导学生对已有方法、协议或设计思想进行质疑，分析局限性并提出改进思路。",
    "学习反思": "引导学生回顾学习过程，总结理解变化、交互收获、薄弱点和后续改进方向。"
}