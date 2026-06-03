"""
Class-level statistical analysis from multiple score records.
"""

from collections import Counter, defaultdict
from data_store import list_scores, INTERACTION_TYPES


def compute_class_analysis(scores: list = None) -> dict:
    """Aggregate all scores into class_analysis.json format."""
    if scores is None:
        scores = list_scores()

    if not scores:
        return _empty_analysis()

    total = len(scores)
    total_scores = [s.get("total_score", 0) for s in scores]
    avg = round(sum(total_scores) / total, 1)
    max_s = max(total_scores)
    min_s = min(total_scores)
    excellent = sum(1 for s in total_scores if s >= 85)
    passing = sum(1 for s in total_scores if s >= 60)

    # Score distribution buckets
    buckets = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "60以下": 0}
    for s in total_scores:
        if s >= 90: buckets["90-100"] += 1
        elif s >= 80: buckets["80-89"] += 1
        elif s >= 70: buckets["70-79"] += 1
        elif s >= 60: buckets["60-69"] += 1
        else: buckets["60以下"] += 1

    # Interaction stats
    all_rounds = []
    type_totals = Counter()
    depth_counter = Counter()
    for s in scores:
        ia = s.get("interaction_analysis", {})
        rounds = ia.get("total_rounds", 0)
        all_rounds.append(rounds)
        types = ia.get("interaction_types", {})
        for t, cnt in types.items():
            type_totals[t] += cnt
        depth = ia.get("depth_level", "一般")
        depth_counter[depth] += 1

    avg_rounds = round(sum(all_rounds) / total, 1) if all_rounds else 0
    most_common = [t for t, _ in type_totals.most_common(3)]

    # Knowledge weaknesses
    weak_counter = Counter()
    missing_counter = Counter()
    for s in scores:
        ka = s.get("knowledge_analysis", {})
        for w in ka.get("weak_points", []):
            weak_counter[w] += 1
        for m in ka.get("missing_points", []):
            missing_counter[m] += 1

    weak_kps = [
        {"knowledge_point": kp, "affected_count": cnt,
         "problem": f"共{cnt}位学生在此知识点存在薄弱"}
        for kp, cnt in weak_counter.most_common(5)
    ]

    # Sub-score averages
    def avg_sub(key):
        vals = [s.get("scores", {}).get(key, 0) for s in scores]
        return round(sum(vals) / len(vals), 1) if vals else 0

    return {
        "student_count": total,
        "score_statistics": {
            "average_score": avg,
            "max_score": max_s,
            "min_score": min_s,
            "excellent_rate": round(excellent / total, 3),
            "pass_rate": round(passing / total, 3),
            "distribution": buckets
        },
        "sub_score_averages": {
            "interaction_quality": avg_sub("interaction_quality"),
            "knowledge_mastery": avg_sub("knowledge_mastery"),
            "presentation": avg_sub("presentation"),
            "reflection": avg_sub("reflection")
        },
        "interaction_statistics": {
            "average_rounds": avg_rounds,
            "most_common_types": most_common,
            "type_distribution": dict(type_totals),
            "depth_distribution": dict(depth_counter)
        },
        "weak_knowledge_points": weak_kps,
        "summary": _generate_summary(avg, avg_rounds, most_common, weak_kps)
    }


def _empty_analysis() -> dict:
    return {
        "student_count": 0,
        "score_statistics": {
            "average_score": 0, "max_score": 0, "min_score": 0,
            "excellent_rate": 0, "pass_rate": 0,
            "distribution": {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "60以下": 0}
        },
        "sub_score_averages": {
            "interaction_quality": 0, "knowledge_mastery": 0,
            "presentation": 0, "reflection": 0
        },
        "interaction_statistics": {
            "average_rounds": 0, "most_common_types": [],
            "type_distribution": {t: 0 for t in INTERACTION_TYPES},
            "depth_distribution": {}
        },
        "weak_knowledge_points": [],
        "summary": "暂无学生成果数据。"
    }


def _generate_summary(avg, avg_rounds, most_common, weak_kps) -> str:
    parts = []
    if avg >= 85:
        parts.append(f"班级整体表现优秀，平均分{avg}分。")
    elif avg >= 70:
        parts.append(f"班级整体表现良好，平均分{avg}分。")
    else:
        parts.append(f"班级整体有较大提升空间，平均分{avg}分。")

    if avg_rounds >= 10:
        parts.append(f"学生平均交互{avg_rounds}轮，达到交互要求。")
    else:
        parts.append(f"学生平均交互{avg_rounds}轮，未达到≥10轮的要求，需加强引导。")

    if most_common:
        parts.append(f"最常见的交互方式为：{'、'.join(most_common)}。")

    if weak_kps:
        kp_names = '、'.join(w['knowledge_point'] for w in weak_kps[:3])
        parts.append(f"群体薄弱知识点集中在：{kp_names}，建议重点复习。")

    return ''.join(parts)
