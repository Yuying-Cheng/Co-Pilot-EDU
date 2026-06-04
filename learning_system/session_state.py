# learning_system/session_state.py

"""当前桌面会话的章节上下文，无需持久化。"""

_ACTIVE_CHAPTER_IDS: set = set()


def register_chapter(chapter_id: str) -> None:
    if chapter_id:
        _ACTIVE_CHAPTER_IDS.add(chapter_id)


def current_chapters() -> set:
    """返回本次会话中已导入/激活的章节 ID 集合。"""
    return set(_ACTIVE_CHAPTER_IDS)


def clear() -> None:
    _ACTIVE_CHAPTER_IDS.clear()