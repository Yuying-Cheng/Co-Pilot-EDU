"""
session_state_bridge.py
统一兼容 learning_system/session_state.py 的调用接口
"""
try:
    from session_state import current_chapters, register_chapter, clear
except ImportError:
    _chapters = set()
    def current_chapters(): return set(_chapters)
    def register_chapter(cid): _chapters.add(cid)
    def clear(): _chapters.clear()
