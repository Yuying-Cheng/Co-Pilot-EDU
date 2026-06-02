"""评价模块统一常量。"""
INTERACTION_TYPES = [
    "询问", "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"
]
DEEP_INTERACTION_TYPES = {
    "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"
}
SCORE_LIMITS = {
    "interaction_quality": 50,
    "knowledge_mastery": 25,
    "presentation": 15,
    "reflection": 10,
}
DEFAULT_MIN_ROUNDS = 10
