"""基于规则的七类交互方式识别器（第一周原型）。"""
from __future__ import annotations
import re
from typing import Dict, List
from .constants import INTERACTION_TYPES

PATTERNS: Dict[str, List[str]] = {
    "询问": [
        r"[？?]",
        r"什么是|为什么|如何|怎样|怎么|请解释|请说明|能否|是否|讲一下|解释一下|介绍一下|说明一下|再讲|再解释",
    ],
    "表达见解": [r"我认为|我觉得|我理解|我的理解|在我看来|我总结|也就是说|换句话说"],
    "审辨": [r"不一定|不认同|有问题|不准确|错误|反例|质疑|验证|是否真的|并不等于|不成立"],
    "猜想": [r"我猜|猜想|假设|会不会|是否可能|如果.+那么|我推测"],
    "想象": [r"想象|类比|比作|好像|生活例子|场景|像.+一样"],
    "创新": [r"改进|优化|重新设计|新方法|变体|推广|我设计|能不能改成"],
}


def classify_interaction(student_input: str, previous_model_output: str = "") -> List[str]:
    """返回一轮学生输入涉及的交互类型列表；一轮可以同时属于多类。"""
    text = (student_input or "").strip()
    types: List[str] = []
    for interaction_type, patterns in PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            types.append(interaction_type)
    mentor_question = bool(re.search(r"你认为|思考|试着|如果|为什么|你能否|你会如何|该怎样", previous_model_output or ""))
    student_reasoning = bool(re.search(r"我认为|因为|所以|因此|可以|不需要|应该|首先|这说明", text))
    if mentor_question and student_reasoning:
        types.append("苏格拉底回答")
    if not types and ("?" in text or "？" in text):
        types.append("询问")
    return [kind for kind in INTERACTION_TYPES if kind in set(types)]
