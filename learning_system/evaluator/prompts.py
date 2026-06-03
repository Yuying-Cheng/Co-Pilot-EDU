"""Prompts for the second-week semantic evaluation workflow."""
from __future__ import annotations

import json
from typing import Any, Dict, List


INTERACTION_TYPES_V2 = ["询问", "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"]


INTERACTION_ANALYSIS_PROMPT = """你需要评价学生与大模型的学习交互过程。

固定七类交互方式只能从以下列表中选择，可多选，不要新增类别：
{interaction_types}

评价重点：
1. 每轮学生输入是否有效，是否只是刷轮数、重复、空泛请求。
2. 每轮学生输入属于哪些交互类型，并给出简短理由。
3. 第2轮及以后是否承接上一轮模型输出，是否围绕同一问题继续推进。
4. 是否形成“接收-反馈-思辨-创造”的探究链。
5. 是否体现主动质疑、比较分析、个人观点、猜想验证、修正理解。

请只输出 JSON，格式如下：
{{
  "rounds": [
    {{
      "round": 1,
      "interaction_types": ["询问"],
      "reason": "简短理由",
      "is_effective": true,
      "is_follow_up": false,
      "follow_up_target": "",
      "continuity_level": "无"
    }}
  ],
  "continuity": {{
    "follow_up_count": 0,
    "continuity_level": "弱",
    "has_inquiry_chain": false,
    "reason": "总体连续性判断"
  }},
  "depth": {{
    "has_questioning": false,
    "has_error_correction": false,
    "has_comparison": false,
    "has_personal_viewpoint": false,
    "has_hypothesis_testing": false,
    "is_answer_scraping": false,
    "active_thinking_level": "弱",
    "depth_level": "较浅",
    "depth_reason": "总体深度判断"
  }},
  "evidence": [
    {{"round": 1, "type": "询问", "reason": "典型证据"}}
  ],
  "problems": ["主要不足"]
}}

任务要求：
{task}

对话记录：
{dialogues}
"""


KNOWLEDGE_ANALYSIS_PROMPT = """你需要评价学生提交材料对任务关联知识点的覆盖、成果表达清晰度和学习反思质量。

知识点覆盖状态只能使用：充分覆盖、部分覆盖、未覆盖。
不要直接给总分，只识别证据和等级。

请只输出 JSON，格式如下：
{{
  "knowledge_points": [
    {{
      "id": "kp001",
      "name": "知识点名称",
      "coverage": "部分覆盖",
      "evidence": "学生材料中的证据"
    }}
  ],
  "missing_points": ["kp001"],
  "weak_points": ["知识点名称"],
  "clarity": {{
    "clarity_score": 10,
    "structure": "较清晰",
    "strengths": ["优点"],
    "problems": ["问题"],
    "is_answer_pileup": false
  }},
  "reflection": {{
    "reflection_score": 6,
    "level": "一般",
    "strengths": ["优点"],
    "problems": ["问题"]
  }}
}}

任务信息：
{task}

任务关联知识点：
{knowledge_points}

对话记录：
{dialogues}

最终报告：
{final_report}

学习反思：
{reflection}
"""


COMMENT_GENERATION_PROMPT = """请根据以下评分结果生成一段教师风格评语，包含优点、不足和改进建议。只输出 JSON：
{{"comment": "评语文本"}}

评分结果：
{score}
"""


def to_json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_interaction_prompt(task: Dict[str, Any], dialogues: List[Dict[str, Any]]) -> str:
    return INTERACTION_ANALYSIS_PROMPT.format(
        interaction_types=to_json_text(INTERACTION_TYPES_V2),
        task=to_json_text(task),
        dialogues=to_json_text(dialogues),
    )


def build_knowledge_prompt(
    task: Dict[str, Any],
    knowledge_points: List[Dict[str, Any]],
    dialogues: List[Dict[str, Any]],
    final_report: str,
    reflection: str,
) -> str:
    return KNOWLEDGE_ANALYSIS_PROMPT.format(
        task=to_json_text(task),
        knowledge_points=to_json_text(knowledge_points),
        dialogues=to_json_text(dialogues),
        final_report=final_report or "",
        reflection=reflection or "",
    )
