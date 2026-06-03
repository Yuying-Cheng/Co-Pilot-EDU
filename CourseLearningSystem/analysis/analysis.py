from collections import Counter

INTERACTION_TYPES = ["询问", "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"]

def compute_class_analysis(scores_list: list) -> dict:
    if not scores_list:
        return _empty_analysis()

    total = len(scores_list)
    total_scores = [s.get("total_score", 0) for s in scores_list]
    avg = round(sum(total_scores) / total, 1)

    buckets = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "60以下": 0}
    for s in total_scores:
        if s >= 90: buckets["90-100"] += 1
        elif s >= 80: buckets["80-89"] += 1
        elif s >= 70: buckets["70-79"] += 1
        elif s >= 60: buckets["60-69"] += 1
        else: buckets["60以下"] += 1

    all_rounds = []
    type_counter = Counter()

    for s in scores_list:
        ia = s.get("interaction_analysis", {})
        all_rounds.append(ia.get("valid_rounds", 0))
        types_dict = ia.get("interaction_types", {})
        for t_name, count in types_dict.items():
            type_counter[t_name] += count

    avg_rounds = round(sum(all_rounds) / total, 1) if all_rounds else 0
    most_common = [k for k, v in type_counter.most_common(3)]

    weak_counter = Counter()
    for s in scores_list:
        ka = s.get("knowledge_analysis", {})
        for point in ka.get("weak_points", []):
            if point:
                weak_counter[str(point)] += 1
    weak_kps = [
        {"knowledge_point": point, "affected_count": count}
        for point, count in weak_counter.most_common()
    ]

    return {
        "student_count": total,
        "score_statistics": {
            "average_score": avg,
            "max_score": max(total_scores),
            "min_score": min(total_scores),
            "distribution": buckets
        },
        "interaction_statistics": {
            "average_rounds": avg_rounds,
            "most_common_types": most_common,
            "type_distribution": dict(type_counter)
        },
        "weak_knowledge_points": weak_kps,
        "summary": _generate_summary(avg, avg_rounds, most_common, weak_kps)
    }

def _empty_analysis() -> dict:
    return {
        "student_count": 0,
        "score_statistics": {
            "average_score": 0, "max_score": 0, "min_score": 0,
            "distribution": {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "60以下": 0}
        },
        "interaction_statistics": {
            "average_rounds": 0, "most_common_types": [],
            "type_distribution": {t: 0 for t in INTERACTION_TYPES}
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
        parts.append(f"班级整体表现一般，平均分{avg}分，需加强辅导。")

    common_text = "、".join(most_common) if most_common else "暂无明显集中类型"
    parts.append(f"人均有效交互{avg_rounds}次，常用交互方式为{common_text}。")
    if weak_kps:
        names = [item["knowledge_point"] for item in weak_kps[:3]]
        parts.append(f"全班共性的薄弱知识点集中在：{'、'.join(names)}等。")
    return " ".join(parts)
