"""In-memory course context for the current desktop session."""

CURRENT_CHAPTER_IDS = set()


def register_chapter(chapter_id: str) -> None:
    if chapter_id:
        CURRENT_CHAPTER_IDS.add(chapter_id)


def current_chapters():
    return set(CURRENT_CHAPTER_IDS)
