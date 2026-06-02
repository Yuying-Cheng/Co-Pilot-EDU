"""
Data models and local JSON storage
"""

import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COURSES_DIR = os.path.join(DATA_DIR, "courses")
SUBMISSIONS_DIR = os.path.join(DATA_DIR, "submissions")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

for d in [DATA_DIR, COURSES_DIR, SUBMISSIONS_DIR, SCORES_DIR]:
    os.makedirs(d, exist_ok=True)

INTERACTION_TYPES = ["询问", "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Course / Knowledge ────────────────────────────────────────────────────────

def save_course(knowledge: dict) -> str:
    """Save knowledge.json and return chapter_id."""
    cid = knowledge.get("chapter_id") or f"ch_{uuid.uuid4().hex[:6]}"
    knowledge["chapter_id"] = cid
    knowledge["created_at"] = datetime.now().isoformat()
    path = os.path.join(COURSES_DIR, f"{cid}_knowledge.json")
    _save_json(path, knowledge)
    return cid

def load_course(chapter_id: str) -> Optional[dict]:
    path = os.path.join(COURSES_DIR, f"{chapter_id}_knowledge.json")
    if os.path.exists(path):
        return _load_json(path)
    return None

def list_courses() -> List[dict]:
    courses = []
    for fn in sorted(os.listdir(COURSES_DIR)):
        if fn.endswith("_knowledge.json"):
            data = _load_json(os.path.join(COURSES_DIR, fn))
            courses.append(data)
    return courses


# ── Tasks ─────────────────────────────────────────────────────────────────────

def save_tasks(chapter_id: str, tasks: dict):
    path = os.path.join(COURSES_DIR, f"{chapter_id}_tasks.json")
    tasks["chapter_id"] = chapter_id
    tasks["updated_at"] = datetime.now().isoformat()
    _save_json(path, tasks)

def load_tasks(chapter_id: str) -> Optional[dict]:
    path = os.path.join(COURSES_DIR, f"{chapter_id}_tasks.json")
    if os.path.exists(path):
        return _load_json(path)
    return None

def list_task_files() -> List[dict]:
    result = []
    for fn in sorted(os.listdir(COURSES_DIR)):
        if fn.endswith("_tasks.json"):
            data = _load_json(os.path.join(COURSES_DIR, fn))
            result.append(data)
    return result


# ── Submissions ───────────────────────────────────────────────────────────────

def save_submission(submission: dict) -> str:
    sid = submission.get("submission_id") or f"sub_{uuid.uuid4().hex[:8]}"
    submission["submission_id"] = sid
    submission["submitted_at"] = datetime.now().isoformat()
    path = os.path.join(SUBMISSIONS_DIR, f"{sid}.json")
    _save_json(path, submission)
    return sid

def load_submission(sid: str) -> Optional[dict]:
    path = os.path.join(SUBMISSIONS_DIR, f"{sid}.json")
    if os.path.exists(path):
        return _load_json(path)
    return None

def list_submissions() -> List[dict]:
    subs = []
    for fn in sorted(os.listdir(SUBMISSIONS_DIR)):
        if fn.endswith(".json"):
            subs.append(_load_json(os.path.join(SUBMISSIONS_DIR, fn)))
    return subs


# ── Scores ────────────────────────────────────────────────────────────────────

def save_score(score: dict) -> str:
    sid = score.get("submission_id", f"score_{uuid.uuid4().hex[:8]}")
    score["scored_at"] = datetime.now().isoformat()
    path = os.path.join(SCORES_DIR, f"{sid}_score.json")
    _save_json(path, score)
    return sid

def load_score(submission_id: str) -> Optional[dict]:
    path = os.path.join(SCORES_DIR, f"{submission_id}_score.json")
    if os.path.exists(path):
        return _load_json(path)
    return None

def list_scores() -> List[dict]:
    scores = []
    for fn in sorted(os.listdir(SCORES_DIR)):
        if fn.endswith("_score.json"):
            scores.append(_load_json(os.path.join(SCORES_DIR, fn)))
    return scores
