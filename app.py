import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from functools import lru_cache

import requests
from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env located next to this file.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

ENDPOINT = os.getenv("ENDPOINT")
API_KEY = os.getenv("LM_STUDIO_API_KEY")

if not ENDPOINT or not API_KEY:
    raise RuntimeError("ENDPOINT and LM_STUDIO_API_KEY must be set in .env")

DATA_DIR = Path("/app/data")
README_PATH = Path("/app/README.md")
APP_DIR = Path(__file__).resolve().parent
FAVICON_PATH = APP_DIR / "favicon.ico"
SETTINGS_PATH = DATA_DIR / "settings" / "settings.json"
BOOK_PLANNING_PATH = APP_DIR / "prompts" / "book_planning.js"
PREMISE_SKILL_PATH = APP_DIR / "skills" / "author" / "premise" / "SKILL.md"
BOOK_BIBLE_SKILL_PATH = APP_DIR / "skills" / "author" / "book-bible" / "SKILL.md"
OUTLINE_SKILL_PATH = APP_DIR / "skills" / "author" / "outline" / "SKILL.md"
CONTINUITY_CHECK_SKILL_PATH = APP_DIR / "skills" / "author" / "continuity-check" / "SKILL.md"
WRITE_POLISH_PATH = APP_DIR / "prompts" / "write_polish.js"
WRITE_SKILL_PATH = APP_DIR / "skills" / "author" / "write" / "SKILL.md"
CHAPTERS_FOLDER_NAME = "Chapters"
WRITING_STATE_FILENAME = "writing_state.json"
WRITING_LOCK_FILENAME = ".writing.lock"
CHAPTER_GENERATION_TIMEOUT_SECONDS = int(os.getenv("CHAPTER_GENERATION_TIMEOUT_SECONDS", "900"))
CHAPTER_AUTO_RETRIES = 2
CHAPTER_WORD_COUNT_MARGIN_RATIO = 0.20
ERROR_LOG_PATH = DATA_DIR / "error_logs.jsonl"
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _log_error(event: str, message: str, context: dict | None = None, stack: str | None = None) -> str:
    """Append structured error information to persistent logs and return log id."""
    log_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    entry = {
        "id": log_id,
        "timestamp": _now_iso_utc(),
        "event": event,
        "message": message,
        "context": context or {},
    }
    if stack:
        entry["stack"] = stack

    try:
        ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except Exception as exc:
        app.logger.error(f"Failed to write error log: {exc}")

    return log_id


def _api_error(status_code: int, message: str, event: str, context: dict | None = None, stack: str | None = None):
    log_id = _log_error(event=event, message=message, context=context, stack=stack)
    return jsonify(error=message, logId=log_id), status_code


def _read_error_logs(limit: int = 200) -> list[dict]:
    if not ERROR_LOG_PATH.exists():
        return []

    rows: list[dict] = []
    try:
        with open(ERROR_LOG_PATH, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        rows.append(payload)
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        app.logger.error(f"Failed to read error logs: {exc}")
        return []

    rows.reverse()
    return rows[: max(1, min(limit, 1000))]

STORY_LENGTHS = {
    "short-story": {
        "storyType": "Short Story",
        "totalWords": 10000,
        "totalChapters": 5,
        "approxWordsPerChapter": 2000,
    },
    "novella": {
        "storyType": "Novella",
        "totalWords": 20000,
        "totalChapters": 10,
        "approxWordsPerChapter": 2000,
    },
    "novel": {
        "storyType": "Novel",
        "totalWords": 50000,
        "totalChapters": 15,
        "approxWordsPerChapter": 3300,
    },
    "epic": {
        "storyType": "Epic",
        "totalWords": 80000,
        "totalChapters": 24,
        "approxWordsPerChapter": 3300,
    },
}


def _save_interaction(prompt: str, response: dict):
    """Persist the prompt and response to a timestamped JSON file."""
    filename = DATA_DIR / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as fp:
        json.dump({"prompt": prompt, "response": response}, fp, indent=2)


def _fetch_models():
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        resp = requests.get(f"{ENDPOINT}/v1/models", headers=headers, timeout=5)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]
    except Exception as e:
        app.logger.error(f"Failed to fetch models: {e}")
        return []


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        app.logger.error(f"Failed to read JSON file {path}: {e}")
        return {}


def _read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_premise_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Develop premise'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Develop premise prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_character_profiles_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Character profiles'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Character profiles prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_chapter_outline_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Chapter-by-chapter outline'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Chapter-by-chapter outline prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_synopsis_generation_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Synopsis generation'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Synopsis generation prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_review_refine_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Review & refine plan'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Review & refine plan prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_contradiction_checks_prompt_template() -> str:
    content = _read_text_file(BOOK_PLANNING_PATH)
    match = re.search(
        r"label:\s*'Contradiction checks'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Contradiction checks prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_premise_skill_text() -> str:
    content = _read_text_file(PREMISE_SKILL_PATH)
    if not content:
        raise RuntimeError("Could not load premise skill instructions")

    lines = content.splitlines()
    if lines[:1] == ["---"]:
        try:
            end_index = lines[1:].index("---") + 1
            lines = lines[end_index + 1 :]
        except ValueError:
            pass

    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def _load_book_bible_skill_text() -> str:
    content = _read_text_file(BOOK_BIBLE_SKILL_PATH)
    if not content:
        raise RuntimeError("Could not load book-bible skill instructions")

    lines = content.splitlines()
    if lines[:1] == ["---"]:
        try:
            end_index = lines[1:].index("---") + 1
            lines = lines[end_index + 1 :]
        except ValueError:
            pass

    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def _load_outline_skill_text() -> str:
    content = _read_text_file(OUTLINE_SKILL_PATH)
    if not content:
        raise RuntimeError("Could not load outline skill instructions")

    lines = content.splitlines()
    if lines[:1] == ["---"]:
        try:
            end_index = lines[1:].index("---") + 1
            lines = lines[end_index + 1 :]
        except ValueError:
            pass

    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def _load_continuity_check_skill_text() -> str:
    content = _read_text_file(CONTINUITY_CHECK_SKILL_PATH)
    if not content:
        raise RuntimeError("Could not load continuity-check skill instructions")

    lines = content.splitlines()
    if lines[:1] == ["---"]:
        try:
            end_index = lines[1:].index("---") + 1
            lines = lines[end_index + 1 :]
        except ValueError:
            pass

    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def _load_write_chapter_prompt_template() -> str:
    content = _read_text_file(WRITE_POLISH_PATH)
    match = re.search(
        r"label:\s*'Write Chapter \{\{chapterNumber\}\}'.*?promptTemplate:\s*`(?P<prompt>.*?)`,\s*",
        content,
        re.S,
    )
    if not match:
        raise RuntimeError("Could not load Write Chapter prompt template")
    return match.group("prompt")


@lru_cache(maxsize=1)
def _load_write_skill_text() -> str:
    content = _read_text_file(WRITE_SKILL_PATH)
    if not content:
        raise RuntimeError("Could not load write skill instructions")

    lines = content.splitlines()
    if lines[:1] == ["---"]:
        try:
            end_index = lines[1:].index("---") + 1
            lines = lines[end_index + 1 :]
        except ValueError:
            pass

    return "\n".join(lines).strip()


def _load_global_settings() -> dict:
    return _read_json_file(SETTINGS_PATH)


def _load_project_settings(project_dir: Path) -> dict:
    settings = _read_json_file(project_dir / "settings.json")
    return settings


def _load_project_idea(project_dir: Path) -> str:
    for filename in ("IDEA.md", "idea.md"):
        file_path = project_dir / filename
        if file_path.exists():
            return _read_text_file(file_path).strip()
    return ""


def _now_iso_utc() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _chapters_dir(project_dir: Path) -> Path:
    return project_dir / CHAPTERS_FOLDER_NAME


def _chapter_file_path(project_dir: Path, chapter_number: int) -> Path:
    return _chapters_dir(project_dir) / f"CHAPTER_{chapter_number}.md"


def _writing_state_path(project_dir: Path) -> Path:
    return project_dir / WRITING_STATE_FILENAME


def _writing_lock_path(project_dir: Path) -> Path:
    return project_dir / WRITING_LOCK_FILENAME


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _resolve_timeout_seconds(project_settings: dict, requested_timeout: int | None = None) -> int:
    """Resolve timeout with precedence: request override -> project settings -> env/default."""
    timeout = None

    if isinstance(requested_timeout, int) and requested_timeout > 0:
        timeout = requested_timeout
    else:
        project_timeout = project_settings.get("writingTimeoutSeconds") if isinstance(project_settings, dict) else None
        if isinstance(project_timeout, int) and project_timeout > 0:
            timeout = project_timeout

    if timeout is None:
        timeout = CHAPTER_GENERATION_TIMEOUT_SECONDS

    # Keep values in a sane range.
    timeout = max(30, min(int(timeout), 7200))
    return timeout


def _resolve_word_count_margin_ratio(project_settings: dict) -> float:
    """Resolve chapter word count margin ratio, defaulting to 20%."""
    default_ratio = CHAPTER_WORD_COUNT_MARGIN_RATIO
    if not isinstance(project_settings, dict):
        return default_ratio

    # Optional override in per-project settings, for example 0.2 for 20%.
    raw_ratio = project_settings.get("writingWordCountMarginRatio")
    if isinstance(raw_ratio, (int, float)):
        return max(0.0, min(float(raw_ratio), 2.0))

    return default_ratio


def _analyze_overlength_chapter(chapter_text: str, target_word_count: int, margin_ratio: float) -> dict:
    """Analyze overlength chapter output for repeated-paragraph hallucination patterns."""
    total_words = _count_words(chapter_text)
    allowed_words = int(target_word_count * (1.0 + margin_ratio))

    normalized_paragraphs = []
    for block in re.split(r"\n\s*\n", chapter_text or ""):
        normalized = re.sub(r"\s+", " ", block).strip().lower()
        if _count_words(normalized) >= 8:
            normalized_paragraphs.append(normalized)

    paragraph_total = len(normalized_paragraphs)
    counts: dict[str, int] = {}
    for paragraph in normalized_paragraphs:
        counts[paragraph] = counts.get(paragraph, 0) + 1

    repeated_instances = sum((count - 1) for count in counts.values() if count > 1)
    max_repeat_count = max(counts.values(), default=1)
    duplicate_ratio = (repeated_instances / paragraph_total) if paragraph_total > 0 else 0.0

    suspicious = duplicate_ratio >= 0.15 or max_repeat_count >= 3
    reason = ""
    if suspicious:
        reason = (
            f"repetition suspected: duplicateParagraphRatio={duplicate_ratio:.2f}, "
            f"maxParagraphRepeat={max_repeat_count}"
        )

    return {
        "totalWords": total_words,
        "allowedWords": allowed_words,
        "marginRatio": margin_ratio,
        "paragraphCount": paragraph_total,
        "repeatedParagraphInstances": repeated_instances,
        "duplicateParagraphRatio": round(duplicate_ratio, 4),
        "maxParagraphRepeat": max_repeat_count,
        "suspicious": suspicious,
        "reason": reason,
    }


def _initial_writing_state(settings: dict) -> dict:
    total_chapters = settings.get("totalChapters")
    if not isinstance(total_chapters, int) or total_chapters <= 0:
        total_chapters = 0

    approx_words = settings.get("approxWordsPerChapter")
    if not isinstance(approx_words, int) or approx_words <= 0:
        approx_words = 0

    chapters = {}
    for chapter_number in range(1, total_chapters + 1):
        chapters[str(chapter_number)] = {
            "status": "pending",
            "attempts": 0,
            "wordCount": 0,
            "lastError": "",
            "updatedAt": None,
        }

    return {
        "totalChapters": total_chapters,
        "targetWordsPerChapter": approx_words,
        "currentChapter": 1 if total_chapters > 0 else 0,
        "overallStatus": "not_started",
        "createdAt": _now_iso_utc(),
        "updatedAt": _now_iso_utc(),
        "autoRetries": CHAPTER_AUTO_RETRIES,
        "generationTimeoutSeconds": _resolve_timeout_seconds(settings),
        "wordCountMarginRatio": _resolve_word_count_margin_ratio(settings),
        "chapters": chapters,
    }


def _update_writing_state_progress(state: dict) -> None:
    total_chapters = int(state.get("totalChapters") or 0)
    chapters = state.get("chapters") if isinstance(state.get("chapters"), dict) else {}
    if total_chapters <= 0:
        state["currentChapter"] = 0
        state["overallStatus"] = "not_started"
        state["updatedAt"] = _now_iso_utc()
        return

    completed = 0
    failed = False
    first_open = total_chapters + 1
    for chapter_number in range(1, total_chapters + 1):
        chapter_state = chapters.get(str(chapter_number), {})
        status = chapter_state.get("status")
        if status == "completed":
            completed += 1
        else:
            first_open = min(first_open, chapter_number)
        if status == "failed":
            failed = True

    if completed >= total_chapters:
        state["overallStatus"] = "completed"
        state["currentChapter"] = total_chapters + 1
    elif failed:
        state["overallStatus"] = "paused_failed"
        state["currentChapter"] = first_open if first_open <= total_chapters else total_chapters
    elif completed == 0:
        state["overallStatus"] = "not_started"
        state["currentChapter"] = 1
    else:
        state["overallStatus"] = "in_progress"
        state["currentChapter"] = first_open if first_open <= total_chapters else total_chapters

    state["updatedAt"] = _now_iso_utc()


def _load_writing_state(project_dir: Path, settings: dict) -> dict:
    path = _writing_state_path(project_dir)
    state = _read_json_file(path)
    if not state:
        state = _initial_writing_state(settings)

    total_chapters = settings.get("totalChapters")
    target_words = settings.get("approxWordsPerChapter")
    if not isinstance(total_chapters, int) or total_chapters <= 0:
        total_chapters = int(state.get("totalChapters") or 0)
    if not isinstance(target_words, int) or target_words <= 0:
        target_words = int(state.get("targetWordsPerChapter") or 0)

    state["totalChapters"] = total_chapters
    state["targetWordsPerChapter"] = target_words
    state["generationTimeoutSeconds"] = _resolve_timeout_seconds(settings)
    state["wordCountMarginRatio"] = _resolve_word_count_margin_ratio(settings)
    chapters = state.get("chapters") if isinstance(state.get("chapters"), dict) else {}
    for chapter_number in range(1, total_chapters + 1):
        key = str(chapter_number)
        if key not in chapters:
            chapters[key] = {
                "status": "pending",
                "attempts": 0,
                "wordCount": 0,
                "lastError": "",
                "updatedAt": None,
            }
    state["chapters"] = chapters

    chapters_dir = _chapters_dir(project_dir)
    if chapters_dir.exists() and chapters_dir.is_dir():
        for chapter_number in range(1, total_chapters + 1):
            chapter_path = _chapter_file_path(project_dir, chapter_number)
            if chapter_path.exists() and chapter_path.is_file():
                chapter_text = _read_text_file(chapter_path)
                chapter_state = state["chapters"].get(str(chapter_number), {})
                if chapter_state.get("status") != "completed":
                    chapter_state["status"] = "completed"
                chapter_state["wordCount"] = _count_words(chapter_text)
                chapter_state["updatedAt"] = chapter_state.get("updatedAt") or _now_iso_utc()
                state["chapters"][str(chapter_number)] = chapter_state

    _update_writing_state_progress(state)
    return state


def _save_writing_state(project_dir: Path, state: dict) -> None:
    path = _writing_state_path(project_dir)
    state["updatedAt"] = _now_iso_utc()
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2)


def _acquire_writing_lock(project_dir: Path) -> bool:
    lock_path = _writing_lock_path(project_dir)
    if lock_path.exists():
        try:
            lock_age_seconds = (datetime.utcnow().timestamp() - lock_path.stat().st_mtime)
            if lock_age_seconds > 1800:
                lock_path.unlink(missing_ok=True)
        except Exception:
            return False

    if lock_path.exists():
        return False

    try:
        lock_payload = {
            "lockedAt": _now_iso_utc(),
            "pid": os.getpid(),
        }
        lock_path.write_text(json.dumps(lock_payload), encoding="utf-8")
        return True
    except Exception:
        return False


def _release_writing_lock(project_dir: Path) -> None:
    try:
        _writing_lock_path(project_dir).unlink(missing_ok=True)
    except Exception:
        pass


def _build_write_chapter_prompt(
    chapter_prompt_template: str,
    chapter_number: int,
    total_chapters: int,
    target_word_count: int,
    book_plan_text: str,
    synopsis_text: str,
    character_profiles_text: str,
    previous_chapter_text: str,
) -> str:
    base_prompt = chapter_prompt_template
    base_prompt = base_prompt.replace("{{chapterNumber}}", str(chapter_number))
    base_prompt = base_prompt.replace("{{totalChapters}}", str(total_chapters))
    base_prompt = base_prompt.replace("{{targetWordCount}}", str(target_word_count))

    previous_block = previous_chapter_text.strip() if previous_chapter_text.strip() else "(No previous chapter. Establish a strong opening while adhering to BOOK_PLAN beats.)"

    return f"""{base_prompt}

Project context for this chapter:
=== BOOK_PLAN.md ===
{book_plan_text}

=== SYNOPSIS.md ===
{synopsis_text}

=== CHARACTER_PROFILES.md ===
{character_profiles_text}

=== PREVIOUS_CHAPTER ===
{previous_block}
"""


def _generate_single_chapter(
    project_name: str,
    chapter_number: int,
    force_regenerate: bool = False,
    auto_retries: int = CHAPTER_AUTO_RETRIES,
    timeout_seconds: int | None = None,
) -> dict:
    project_dir = DATA_DIR / project_name
    settings = _read_json_file(project_dir / "settings.json")
    state = _load_writing_state(project_dir, settings)

    total_chapters = int(state.get("totalChapters") or 0)
    if chapter_number < 1 or chapter_number > total_chapters:
        raise ValueError(f"chapterNumber must be between 1 and {total_chapters}")

    chapters_dir = _chapters_dir(project_dir)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    chapter_path = _chapter_file_path(project_dir, chapter_number)
    chapter_key = str(chapter_number)
    chapter_state = state["chapters"].get(chapter_key, {})

    if chapter_path.exists() and chapter_state.get("status") == "completed" and not force_regenerate:
        return {
            "status": "already_completed",
            "chapterNumber": chapter_number,
            "wordCount": int(chapter_state.get("wordCount") or 0),
            "attempts": int(chapter_state.get("attempts") or 0),
            "nextChapter": int(state.get("currentChapter") or chapter_number + 1),
        }

    book_plan_text = _read_text_file(project_dir / "BOOK_PLAN.md").strip()
    synopsis_text = _read_text_file(project_dir / "SYNOPSIS.md").strip()
    character_profiles_text = _read_text_file(project_dir / "CHARACTER_PROFILES.md").strip()

    if not book_plan_text:
        raise RuntimeError("BOOK_PLAN.md not found or empty")
    if not synopsis_text:
        raise RuntimeError("SYNOPSIS.md not found or empty")
    if not character_profiles_text:
        raise RuntimeError("CHARACTER_PROFILES.md not found or empty")

    previous_chapter_text = ""
    if chapter_number > 1:
        previous_path = _chapter_file_path(project_dir, chapter_number - 1)
        if previous_path.exists() and previous_path.is_file():
            previous_chapter_text = _read_text_file(previous_path)

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"
    timeout_seconds = _resolve_timeout_seconds(settings, timeout_seconds)
    margin_ratio = _resolve_word_count_margin_ratio(settings)

    chapter_prompt_template = _load_write_chapter_prompt_template()
    write_skill_text = _load_write_skill_text()
    target_word_count = int(state.get("targetWordsPerChapter") or 0)

    prompt = _build_write_chapter_prompt(
        chapter_prompt_template=chapter_prompt_template,
        chapter_number=chapter_number,
        total_chapters=total_chapters,
        target_word_count=target_word_count,
        book_plan_text=book_plan_text,
        synopsis_text=synopsis_text,
        character_profiles_text=character_profiles_text,
        previous_chapter_text=previous_chapter_text,
    )

    messages = [
        {
            "role": "system",
            "content": f"""You are the AuthorLite chapter writer.
Follow the write skill instructions and output only chapter prose.

Write skill guidance:
{write_skill_text}
""",
        },
        {"role": "user", "content": prompt},
    ]

    max_attempts = max(1, int(auto_retries) + 1)
    last_error = ""

    chapter_state["status"] = "in_progress"
    chapter_state["lastError"] = ""
    chapter_state["updatedAt"] = _now_iso_utc()
    state["chapters"][chapter_key] = chapter_state
    state["overallStatus"] = "in_progress"
    _save_writing_state(project_dir, state)

    for _ in range(max_attempts):
        chapter_state["attempts"] = int(chapter_state.get("attempts") or 0) + 1
        chapter_state["updatedAt"] = _now_iso_utc()
        state["chapters"][chapter_key] = chapter_state
        _save_writing_state(project_dir, state)

        try:
            result = _call_llm(model, messages, timeout_seconds=timeout_seconds)
            chapter_content = _clean_generated_content(_extract_assistant_content(result)).strip()
            if not chapter_content:
                raise RuntimeError("Empty chapter response from model")

            chapter_word_count = _count_words(chapter_content)
            quality_check = None
            if target_word_count > 0:
                allowed_words = int(target_word_count * (1.0 + margin_ratio))
                if chapter_word_count > allowed_words:
                    quality_check = _analyze_overlength_chapter(
                        chapter_text=chapter_content,
                        target_word_count=target_word_count,
                        margin_ratio=margin_ratio,
                    )
                    if quality_check.get("suspicious"):
                        raise RuntimeError(
                            "Chapter failed overlength repetition check: "
                            f"{quality_check.get('reason')}"
                        )

            chapter_path.write_text(chapter_content + "\n", encoding="utf-8")
            chapter_state["status"] = "completed"
            chapter_state["wordCount"] = chapter_word_count
            chapter_state["lastError"] = ""
            chapter_state["updatedAt"] = _now_iso_utc()
            chapter_state["qualityCheck"] = quality_check or {}
            state["chapters"][chapter_key] = chapter_state
            _update_writing_state_progress(state)
            _save_writing_state(project_dir, state)
            _save_interaction(prompt, result)

            return {
                "status": "completed",
                "chapterNumber": chapter_number,
                "wordCount": chapter_state["wordCount"],
                "attempts": int(chapter_state.get("attempts") or 0),
                "nextChapter": int(state.get("currentChapter") or (chapter_number + 1)),
                "filename": chapter_path.name,
                "content": chapter_content,
                "timeoutSeconds": timeout_seconds,
                "qualityCheck": quality_check or {},
            }
        except Exception as exc:
            last_error = str(exc)
            chapter_state["lastError"] = last_error
            chapter_state["updatedAt"] = _now_iso_utc()
            state["chapters"][chapter_key] = chapter_state
            _save_writing_state(project_dir, state)

    chapter_state["status"] = "failed"
    chapter_state["updatedAt"] = _now_iso_utc()
    state["chapters"][chapter_key] = chapter_state
    _update_writing_state_progress(state)
    _save_writing_state(project_dir, state)

    return {
        "status": "failed",
        "chapterNumber": chapter_number,
        "attempts": int(chapter_state.get("attempts") or 0),
        "error": last_error or "Chapter generation failed",
        "nextChapter": int(state.get("currentChapter") or chapter_number),
    }


def _run_chapter_sequence(project_name: str, start_chapter: int, end_chapter: int, timeout_seconds: int | None = None) -> tuple[dict, int]:
    project_dir = DATA_DIR / project_name
    settings = _read_json_file(project_dir / "settings.json")

    if not _acquire_writing_lock(project_dir):
        return {"error": "Writing is already in progress for this project"}, 409

    results = []
    try:
        for chapter_number in range(start_chapter, end_chapter + 1):
            outcome = _generate_single_chapter(
                project_name=project_name,
                chapter_number=chapter_number,
                force_regenerate=False,
                auto_retries=CHAPTER_AUTO_RETRIES,
                timeout_seconds=timeout_seconds,
            )
            results.append(outcome)
            if outcome.get("status") == "failed":
                latest_state = _load_writing_state(project_dir, settings)
                return {
                    "status": "paused_failed",
                    "failedChapter": chapter_number,
                    "results": results,
                    "currentChapter": latest_state.get("currentChapter"),
                    "overallStatus": latest_state.get("overallStatus"),
                }, 502

        latest_state = _load_writing_state(project_dir, settings)
        final_status = "completed_all" if latest_state.get("overallStatus") == "completed" else "in_progress"
        return {
            "status": final_status,
            "results": results,
            "currentChapter": latest_state.get("currentChapter"),
            "overallStatus": latest_state.get("overallStatus"),
        }, 200
    finally:
        _release_writing_lock(project_dir)


def _build_premise_prompt(project_name: str, idea_text: str, project_settings: dict) -> str:
    prompt_template = _load_premise_prompt_template()
    skill_text = _load_premise_skill_text()

    project_summary = [
        f"- Project: {project_name}",
        f"- Story type: {project_settings.get('storyType', 'Unknown')}",
        f"- Total words: {project_settings.get('totalWords', 'Unknown')}",
        f"- Total chapters: {project_settings.get('totalChapters', 'Unknown')}",
        f"- Approx words per chapter: {project_settings.get('approxWordsPerChapter', 'Unknown')}",
    ]

    length_guardrails = {
        "Short Story": "Keep the premise tightly focused, with a small cast and a single central conflict that resolves cleanly within about five chapters.",
        "Novella": "Keep the premise focused but with enough complication for a mid-length arc, avoiding sprawling subplots or a huge cast.",
        "Novel": "Allow for a fuller character arc, layered complications, and enough room for escalating tension across multiple acts.",
        "Epic": "Support a broader scope, more moving parts, and a large-scale arc that still remains coherent at roughly twenty-four chapters.",
    }

    story_type = project_settings.get("storyType", "Novel")
    guardrail = length_guardrails.get(story_type, length_guardrails["Novel"])
    idea_block = idea_text if idea_text else f"Project concept: {project_name}"
    base_prompt = prompt_template.replace("{{description}}", idea_block)

    return f"""{base_prompt}

Project configuration from the project settings file:
{chr(10).join(project_summary)}

Length guardrail for this project:
{guardrail}

Premise skill guidance:
{skill_text}

Write the final answer as markdown for PREMISE.md.
Do not include chatty commentary, follow-up questions, or model control tokens.
Use this structure:
# PREMISE
## Story Configuration
## Logline
## What-If Question
## Core Conflict
## Stakes
## Theme Statement
## Unique Hook
## Genre Promise
## Plot Threads and Story Flow to Preserve
## Market Fit
## Comp Titles
## Next-Step Notes

Keep the premise aligned to the configured length and explicitly note if the concept needs widening or narrowing to fit the target word count and chapter count.
If IDEA.md names specific plot threads, reveal sequences, scene flow, relationship turns, or ending direction, carry them into the dedicated section so later planning phases preserve them.
"""


def _call_llm(model: str, messages: list[dict], timeout_seconds: int | None = None) -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages}
    base = ENDPOINT.rstrip("/")
    request_timeout = timeout_seconds if timeout_seconds and timeout_seconds > 0 else None
    resp = requests.post(f"{base}/v1/chat/completions", headers=headers, json=payload, timeout=request_timeout)

    if resp.status_code != 200:
        app.logger.error(f"LM Studio returned {resp.status_code}: {resp.text}")
        raise RuntimeError(f"LM Studio API error: {resp.text}")

    return resp.json()


def _extract_assistant_content(response: dict) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""

    choice = choices[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")
    if content:
        return content

    delta = choice.get("delta") or {}
    return delta.get("content", "")


def _clean_premise_content(content: str) -> str:
    """Remove leaked control tokens and trailing conversational text."""
    if not content:
        return ""

    cleaned = content.replace("\r\n", "\n").strip()
    cleaned = re.sub(r"<\|channel\|>.*?<\|message\|>", "", cleaned, flags=re.S)
    cleaned = re.sub(r"<\|[^>]+\|>", "", cleaned)

    stop_patterns = [
        r"(?im)^\s*(would you like me to|do you want me to|should i|if you'd like, i can).*$",
        r"(?im)^\s*(let me know if|happy to|i can also|i can draft).*$",
    ]
    for pattern in stop_patterns:
        match = re.search(pattern, cleaned)
        if match:
            cleaned = cleaned[: match.start()].rstrip()

    return cleaned.strip()


def _clean_generated_content(content: str) -> str:
    """Apply the same cleanup used for premise output to generated docs."""
    return _clean_premise_content(content)


def _extract_json_object(content: str) -> dict:
    """Extract and parse a JSON object from model output."""
    if not content:
        raise ValueError("Empty model output")

    cleaned = content.replace("\r\n", "\n").strip()
    cleaned = re.sub(r"<\|channel\|>.*?<\|message\|>", "", cleaned, flags=re.S)
    cleaned = re.sub(r"<\|[^>]+\|>", "", cleaned).strip()

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", cleaned, re.S)
    if fenced:
        candidate = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model output")
        candidate = cleaned[start : end + 1]

    data = json.loads(candidate)
    if not isinstance(data, dict):
        raise ValueError("Model output JSON must be an object")
    return data


@app.errorhandler(Exception)
def handle_unexpected_error(exc: Exception):
    """Log uncaught exceptions with request context and return JSON for API requests."""
    stack = traceback.format_exc()
    context = {
        "path": request.path,
        "method": request.method,
        "query": request.query_string.decode("utf-8", errors="ignore"),
    }
    log_id = _log_error("uncaught_exception", str(exc), context=context, stack=stack)

    # Preserve Flask HTTPException handling if present.
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return exc

    if request.path == "/" or request.path.startswith("/static/"):
        return "Unexpected server error", 500

    return jsonify(error="Unexpected server error", logId=log_id), 500

@app.route("/models", methods=["GET"])
def models_route():
    models = _fetch_models()
    # Return as JSON or can serve dash.html for model discovery
    if request.args.get('html'):
        return render_template("dash.html", models=models, endpoint=ENDPOINT, apiKey=API_KEY)
    return jsonify({"models": models})


@app.route("/", endpoint="index_page")
def index():
    # Serve the new dashboard with model info
    models = _fetch_models()
    return render_template("dash.html", models=models, endpoint=ENDPOINT, apiKey=API_KEY)


@app.route("/favicon.ico")
def favicon():
    """Serve favicon for browser requests to avoid noisy 404 logs."""
    if FAVICON_PATH.exists():
        return send_file(FAVICON_PATH, mimetype="image/x-icon")
    return "", 204


@app.route("/readme", methods=["GET"])
def get_readme():
    """Serve repository README as markdown text for the dashboard."""
    if not README_PATH.exists():
        return jsonify(error="README.md not found"), 404

    try:
        content = README_PATH.read_text(encoding="utf-8")
        return app.response_class(content, mimetype="text/markdown")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    prompt = data.get("prompt")
    if not prompt:
        return jsonify(error="'prompt' field required"), 400

    # Use model from client if provided, otherwise use default
    model = data.get("model", "gpt-oss-20b")

    try:
        result = _call_llm(model, [{"role": "user", "content": prompt}])
    except Exception as e:
        return jsonify(error="LM Studio API error", details=str(e)), 500

    _save_interaction(prompt, result)
    return jsonify(result)


@app.route("/generate-premise", methods=["POST"])
def generate_premise():
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    idea_text = _load_project_idea(project_dir)
    if not idea_text:
        return jsonify(error="IDEA.md not found"), 404

    project_settings = _load_project_settings(project_dir)
    if not project_settings:
        return jsonify(error="Project settings not found"), 404

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"

    prompt = _build_premise_prompt(project_name, idea_text, project_settings)
    messages = [
        {
            "role": "system",
            "content": "You are the AuthorLite premise generator. Produce a polished markdown premise file that follows the requested structure exactly.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        result = _call_llm(model, messages)
        premise_content = _clean_premise_content(_extract_assistant_content(result))
        if not premise_content:
            return jsonify(error="Empty premise response from model"), 502

        premise_path = project_dir / "PREMISE.md"
        premise_path.write_text(premise_content + "\n", encoding="utf-8")
        _save_interaction(prompt, result)
        return jsonify(message="Premise generated", filename="PREMISE.md", content=premise_content)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/generate-character-profiles", methods=["POST"])
def generate_character_profiles():
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    premise_path = project_dir / "PREMISE.md"
    if not premise_path.exists():
        return jsonify(error="PREMISE.md not found"), 404

    premise_text = _read_text_file(premise_path).strip()
    if not premise_text:
        return jsonify(error="PREMISE.md is empty"), 400

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"

    prompt_template = _load_character_profiles_prompt_template()
    skill_text = _load_book_bible_skill_text()
    prompt = prompt_template.replace("{{description}}", premise_text)

    messages = [
        {
            "role": "system",
            "content": "You are the AuthorLite character profile generator. Produce polished markdown that follows the requested structure exactly.",
        },
        {
            "role": "user",
            "content": f"{prompt}\n\nPremise source text:\n{premise_text}\n\nBook-bible skill guidance:\n{skill_text}\n\nWrite the final answer as markdown for CHARACTER_PROFILES.md. Do not include chatty commentary, follow-up questions, or model control tokens.",
        },
    ]

    try:
        result = _call_llm(model, messages)
        profiles_content = _clean_generated_content(_extract_assistant_content(result))
        if not profiles_content:
            return jsonify(error="Empty character profiles response from model"), 502

        profiles_path = project_dir / "CHARACTER_PROFILES.md"
        profiles_path.write_text(profiles_content + "\n", encoding="utf-8")
        _save_interaction(prompt, result)
        return jsonify(message="Character profiles generated", filename="CHARACTER_PROFILES.md", content=profiles_content)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/generate-synopsis", methods=["POST"])
def generate_synopsis():
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    premise_path = project_dir / "PREMISE.md"
    profiles_path = project_dir / "CHARACTER_PROFILES.md"
    if not premise_path.exists():
        return jsonify(error="PREMISE.md not found"), 404
    if not profiles_path.exists():
        return jsonify(error="CHARACTER_PROFILES.md not found"), 404

    premise_text = _read_text_file(premise_path).strip()
    profiles_text = _read_text_file(profiles_path).strip()
    if not premise_text:
        return jsonify(error="PREMISE.md is empty"), 400
    if not profiles_text:
        return jsonify(error="CHARACTER_PROFILES.md is empty"), 400

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"

    source_context = f"""Premise:
{premise_text}

Character Profiles:
{profiles_text}
"""
    chapter_outline_prompt = _load_chapter_outline_prompt_template().replace("{{description}}", source_context)
    synopsis_prompt = _load_synopsis_generation_prompt_template().replace("{{description}}", source_context)
    outline_skill_text = _load_outline_skill_text()

    full_prompt = f"""{chapter_outline_prompt}

{synopsis_prompt}

Outline skill guidance:
{outline_skill_text}

Use BOTH prompt instructions above. Produce one combined markdown file for SYNOPSIS.md with this structure:
# SYNOPSIS
## Chapter-by-Chapter Outline
## One-Page Synopsis
## Three-Page Synopsis

Do not include chatty commentary, follow-up questions, or model control tokens.
"""

    messages = [
        {
            "role": "system",
            "content": "You are the AuthorLite synopsis generator. Produce polished markdown that follows the requested structure exactly.",
        },
        {"role": "user", "content": full_prompt},
    ]

    try:
        result = _call_llm(model, messages)
        synopsis_content = _clean_generated_content(_extract_assistant_content(result))
        if not synopsis_content:
            return jsonify(error="Empty synopsis response from model"), 502

        synopsis_path = project_dir / "SYNOPSIS.md"
        synopsis_path.write_text(synopsis_content + "\n", encoding="utf-8")
        _save_interaction(full_prompt, result)
        return jsonify(message="Synopsis generated", filename="SYNOPSIS.md", content=synopsis_content)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/generate-book-plan", methods=["POST"])
def generate_book_plan():
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    premise_path = project_dir / "PREMISE.md"
    profiles_path = project_dir / "CHARACTER_PROFILES.md"
    synopsis_path = project_dir / "SYNOPSIS.md"

    if not premise_path.exists():
        return jsonify(error="PREMISE.md not found"), 404
    if not profiles_path.exists():
        return jsonify(error="CHARACTER_PROFILES.md not found"), 404
    if not synopsis_path.exists():
        return jsonify(error="SYNOPSIS.md not found"), 404

    premise_text = _read_text_file(premise_path).strip()
    profiles_text = _read_text_file(profiles_path).strip()
    synopsis_text = _read_text_file(synopsis_path).strip()

    if not premise_text:
        return jsonify(error="PREMISE.md is empty"), 400
    if not profiles_text:
        return jsonify(error="CHARACTER_PROFILES.md is empty"), 400
    if not synopsis_text:
        return jsonify(error="SYNOPSIS.md is empty"), 400

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"

    source_context = f"""Premise:
{premise_text}

Character Profiles:
{profiles_text}

Synopsis:
{synopsis_text}
"""

    review_prompt = _load_review_refine_prompt_template().replace("{{description}}", source_context)
    contradiction_prompt = _load_contradiction_checks_prompt_template().replace("{{description}}", source_context)
    continuity_skill_text = _load_continuity_check_skill_text()

    full_prompt = f"""{review_prompt}

{contradiction_prompt}

Continuity-check skill guidance:
{continuity_skill_text}

Use BOTH prompt instructions above to produce a polished, integrated final book plan from all source files.
Write the final answer as markdown for BOOK_PLAN.md with this structure:
# BOOK PLAN
## Executive Summary
## Premise
## Character Profiles
## Outline and Story Flow
## Contradiction Check Findings
## Revisions Applied
## Final Integrated Plan

In Contradiction Check Findings, include ERROR/WARNING/INFO where applicable with concise evidence.
In Revisions Applied, clearly list what changed to resolve contradictions or weak points.
Do not include chatty commentary, follow-up questions, or model control tokens.
"""

    messages = [
        {
            "role": "system",
            "content": "You are the AuthorLite book-plan finalizer. Produce polished markdown that follows the requested structure exactly.",
        },
        {"role": "user", "content": full_prompt},
    ]

    try:
        result = _call_llm(model, messages)
        book_plan_content = _clean_generated_content(_extract_assistant_content(result))
        if not book_plan_content:
            return jsonify(error="Empty book plan response from model"), 502

        book_plan_path = project_dir / "BOOK_PLAN.md"
        book_plan_path.write_text(book_plan_content + "\n", encoding="utf-8")
        _save_interaction(full_prompt, result)
        return jsonify(message="Book plan generated", filename="BOOK_PLAN.md", content=book_plan_content)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/apply-book-plan-revisions", methods=["POST"])
def apply_book_plan_revisions():
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    premise_path = project_dir / "PREMISE.md"
    profiles_path = project_dir / "CHARACTER_PROFILES.md"
    synopsis_path = project_dir / "SYNOPSIS.md"
    book_plan_path = project_dir / "BOOK_PLAN.md"

    required = [premise_path, profiles_path, synopsis_path, book_plan_path]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return jsonify(error=f"Missing required files: {', '.join(missing)}"), 404

    premise_text = _read_text_file(premise_path).strip()
    profiles_text = _read_text_file(profiles_path).strip()
    synopsis_text = _read_text_file(synopsis_path).strip()
    book_plan_text = _read_text_file(book_plan_path).strip()

    if not all([premise_text, profiles_text, synopsis_text, book_plan_text]):
        return jsonify(error="One or more required files are empty"), 400

    global_settings = _load_global_settings()
    model = global_settings.get("model") or "gpt-oss-20b"
    continuity_skill_text = _load_continuity_check_skill_text()

    prompt = f"""Apply the revisions identified in BOOK_PLAN.md to the full project plan.

Source files:
=== PREMISE.md ===
{premise_text}

=== CHARACTER_PROFILES.md ===
{profiles_text}

=== SYNOPSIS.md ===
{synopsis_text}

=== BOOK_PLAN.md ===
{book_plan_text}

Continuity-check guidance:
{continuity_skill_text}

Task:
1. Resolve contradictions and weaknesses described in BOOK_PLAN.md across all planning documents.
2. Rewrite and return updated versions of PREMISE.md, CHARACTER_PROFILES.md, SYNOPSIS.md, and BOOK_PLAN.md.
3. BOOK_PLAN.md must be the final consolidated plan for chapter-writing injection.
4. BOOK_PLAN.md must NOT contain these sections or equivalents:
   - Contradiction Check Findings
   - Continuity Check Summary / summary of findings
   - Revisions Applied
   - Final Integrated Plan
5. Keep all outputs in clean markdown, with no chatty commentary, no follow-up questions, and no model control tokens.

Output strictly as JSON with exactly these keys:
{{
  "PREMISE.md": "...markdown...",
  "CHARACTER_PROFILES.md": "...markdown...",
  "SYNOPSIS.md": "...markdown...",
  "BOOK_PLAN.md": "...markdown..."
}}
Do not include any text before or after the JSON object.
"""

    messages = [
        {
            "role": "system",
            "content": "You are the AuthorLite revision applier. Return only valid JSON with updated markdown file contents.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        result = _call_llm(model, messages)
        raw_content = _extract_assistant_content(result)
        payload = _extract_json_object(raw_content)

        required_keys = ["PREMISE.md", "CHARACTER_PROFILES.md", "SYNOPSIS.md", "BOOK_PLAN.md"]
        missing_keys = [k for k in required_keys if k not in payload]
        if missing_keys:
            return jsonify(error=f"Missing keys in model output: {', '.join(missing_keys)}"), 502

        revised = {}
        for key in required_keys:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                return jsonify(error=f"Invalid content for {key}"), 502
            revised[key] = _clean_generated_content(value)

        (project_dir / "PREMISE.md").write_text(revised["PREMISE.md"] + "\n", encoding="utf-8")
        (project_dir / "CHARACTER_PROFILES.md").write_text(revised["CHARACTER_PROFILES.md"] + "\n", encoding="utf-8")
        (project_dir / "SYNOPSIS.md").write_text(revised["SYNOPSIS.md"] + "\n", encoding="utf-8")
        (project_dir / "BOOK_PLAN.md").write_text(revised["BOOK_PLAN.md"] + "\n", encoding="utf-8")

        _save_interaction(prompt, result)
        return jsonify(
            message="Revisions applied",
            filename="BOOK_PLAN.md",
            content=revised["BOOK_PLAN.md"],
            updatedFiles=required_keys,
        )
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/save-settings", methods=["POST"])
def save_settings():
    """Receive settings from frontend and save them (handled entirely server-side)"""
    data = request.get_json(force=True)
    model = data.get("model")
    context_limit = data.get("contextLimit", 4096)

    # Store in persistent volume at /app/data/settings/
    settings_path = "/app/data/settings/settings.json"
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    
    settings_data = {
        "model": model,
        "contextLimit": context_limit
    }
    
    with open(settings_path, 'w') as f:
        json.dump(settings_data, f, indent=2)

    return jsonify({"message": "Settings saved"})


@app.route("/get-settings", methods=["GET"])
def get_settings():
    """Return current settings from Flask backend (never call external API)"""
    
    settings_path = "/app/data/settings/settings.json"
    
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        # Return defaults if no saved settings
        return jsonify({})


@app.route("/error-logs", methods=["GET"])
def get_error_logs():
    try:
        raw_limit = request.args.get("limit", "200")
        limit = int(raw_limit)
    except ValueError:
        return _api_error(400, "limit must be an integer", "error_logs_bad_limit", {"limit": request.args.get("limit")})

    logs = _read_error_logs(limit=limit)
    return jsonify(logs=logs)


@app.route("/client-error", methods=["POST"])
def client_error():
    data = request.get_json(force=True) or {}
    event = str(data.get("event") or "client_error")
    message = str(data.get("message") or "Client-side error")
    context = data.get("context")
    if not isinstance(context, dict):
        context = {"rawContext": str(context)} if context is not None else {}
    log_id = _log_error(event=event, message=message, context=context)
    return jsonify(message="Logged", logId=log_id)


@app.route("/get-file", methods=["GET"])
def get_file():
    """Return file content from Flask backend (never call external API)"""
    project = request.args.get("project")
    filename = request.args.get("filename")
    
    if not project or not filename:
        return jsonify(error="Project and filename required"), 400
    
    file_path = DATA_DIR / project / filename

    # Backward-compatible lookup for legacy lowercase IDEA filename.
    if not file_path.exists() and filename == "IDEA.md":
        legacy_path = DATA_DIR / project / "idea.md"
        if legacy_path.exists():
            file_path = legacy_path
    
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                return jsonify(content=f.read())
        except Exception as e:
            return jsonify(error=str(e)), 500
    else:
        return jsonify(error="File not found"), 404


@app.route("/save-file", methods=["POST"])
def save_file():
    """Save file via Flask backend (never call external API)"""
    data = request.get_json(force=True)
    project = data.get("project")
    filename = data.get("filename")
    content = data.get("content")
    
    if not all([project, filename, content]):
        return jsonify(error="All fields required"), 400
    
    file_path = DATA_DIR / project / filename
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return jsonify(message="File saved")
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/create-project", methods=["POST"])
def create_project():
    """Create project via Flask backend (never call external API)"""
    data = request.get_json(force=True)
    project_name = data.get("projectName")
    story_length_key = data.get("storyLength", "novel")

    story_length = STORY_LENGTHS.get(story_length_key)
    
    if not project_name:
        return jsonify(error="Project name required"), 400
    if not story_length:
        return jsonify(error="Story length required"), 400
    
    project_dir = DATA_DIR / project_name
    
    try:
        # Create directory and IDEA.md file
        project_dir.mkdir(parents=True, exist_ok=True)
        idea_path = project_dir / "IDEA.md"
        
        # Create IDEA.md with project title
        project_title = "#" + project_name.replace("/", "\\/").replace("*", "\\*")
        with open(idea_path, 'w') as f:
            f.write(f"{project_title}\n\n")

        settings_path = project_dir / "settings.json"
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(story_length, f, indent=2)
        
        return jsonify(message="Project created")
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/list-files", methods=["GET"])
def list_files():
    """List files for a project so the UI can render a hierarchy."""
    project = request.args.get("project")
    if not project:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    try:
        hidden_internal = {WRITING_STATE_FILENAME, WRITING_LOCK_FILENAME}
        files = sorted([p.name for p in project_dir.iterdir() if p.is_file() and p.name not in hidden_internal])
        folders = []
        for p in sorted([d for d in project_dir.iterdir() if d.is_dir()], key=lambda d: d.name.lower()):
            child_files = sorted([f.name for f in p.iterdir() if f.is_file()])
            folders.append({"name": p.name, "files": child_files})

        return jsonify(files=files, folders=folders)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/list-projects", methods=["GET"])
def list_projects():
    """List projects from Flask backend (never call external API)"""
    try:
        # Exclude internal app directories so they do not appear as user projects.
        excluded = {"settings"}
        projects = [
            d.name
            for d in DATA_DIR.iterdir()
            if d.is_dir() and d.name not in excluded and not d.name.startswith(".")
        ]
        return jsonify(projects=projects)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/start-writing", methods=["POST"])
def start_writing():
    """Create Chapters folder for a project and return writing target metadata."""
    data = request.get_json(force=True)
    project_name = data.get("project")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    settings = _read_json_file(project_dir / "settings.json")
    total_chapters = settings.get("totalChapters")
    if not isinstance(total_chapters, int) or total_chapters <= 0:
        return jsonify(error="Project settings missing valid totalChapters"), 400

    chapters_dir = _chapters_dir(project_dir)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    state = _load_writing_state(project_dir, settings)
    _save_writing_state(project_dir, state)

    chapter_count = 0
    for path in chapters_dir.iterdir():
        if path.is_file() and re.match(r"^CHAPTER_\d+\.md$", path.name, re.I):
            chapter_count += 1

    return jsonify(
        message="Writing stage initialized",
        totalChapters=total_chapters,
        writtenChapters=chapter_count,
        currentChapter=state.get("currentChapter"),
        overallStatus=state.get("overallStatus"),
        generationTimeoutSeconds=state.get("generationTimeoutSeconds"),
    )


@app.route("/writing-progress", methods=["GET"])
def writing_progress():
    """Return chapter writing progress for the selected project."""
    project_name = request.args.get("project")
    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    settings = _read_json_file(project_dir / "settings.json")
    total_chapters = settings.get("totalChapters")
    if not isinstance(total_chapters, int) or total_chapters <= 0:
        total_chapters = 0

    chapters_dir = _chapters_dir(project_dir)
    chapter_numbers = []
    if chapters_dir.exists() and chapters_dir.is_dir():
        for path in chapters_dir.iterdir():
            if not path.is_file():
                continue
            match = re.match(r"^CHAPTER_(\d+)\.md$", path.name, re.I)
            if match:
                chapter_numbers.append(int(match.group(1)))

    chapter_numbers.sort()
    state = _load_writing_state(project_dir, settings)
    chapter_states = state.get("chapters") if isinstance(state.get("chapters"), dict) else {}

    return jsonify(
        totalChapters=total_chapters,
        writtenChapters=len(chapter_numbers),
        chapterNumbers=chapter_numbers,
        writingStarted=chapters_dir.exists() and chapters_dir.is_dir(),
        currentChapter=state.get("currentChapter"),
        overallStatus=state.get("overallStatus"),
        targetWordsPerChapter=state.get("targetWordsPerChapter"),
        generationTimeoutSeconds=state.get("generationTimeoutSeconds"),
        chapterStates=chapter_states,
    )


@app.route("/generate-chapter", methods=["POST"])
def generate_chapter():
    data = request.get_json(force=True)
    project_name = data.get("project")
    chapter_number = data.get("chapterNumber")
    force_regenerate = bool(data.get("forceRegenerate", False))
    timeout_seconds = data.get("timeoutSeconds")

    if not project_name:
        return jsonify(error="Project required"), 400

    try:
        chapter_number = int(chapter_number)
    except (TypeError, ValueError):
        return _api_error(400, "chapterNumber must be an integer", "generate_chapter_bad_input", {"project": project_name, "chapterNumber": chapter_number})

    if timeout_seconds is not None:
        try:
            timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError):
            return _api_error(400, "timeoutSeconds must be an integer", "generate_chapter_bad_timeout", {"project": project_name, "timeoutSeconds": timeout_seconds})

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    if not _acquire_writing_lock(project_dir):
        return _api_error(409, "Writing is already in progress for this project", "generate_chapter_locked", {"project": project_name})

    try:
        outcome = _generate_single_chapter(
            project_name=project_name,
            chapter_number=chapter_number,
            force_regenerate=force_regenerate,
            auto_retries=CHAPTER_AUTO_RETRIES,
            timeout_seconds=timeout_seconds,
        )
        if outcome.get("status") == "failed":
            log_id = _log_error(
                event="generate_chapter_failed",
                message=str(outcome.get("error") or "Chapter generation failed"),
                context={"project": project_name, "chapterNumber": chapter_number, "attempts": outcome.get("attempts")},
            )
            outcome["logId"] = log_id
            return jsonify(outcome), 502
        return jsonify(outcome)
    except ValueError as e:
        return _api_error(400, str(e), "generate_chapter_value_error", {"project": project_name, "chapterNumber": chapter_number})
    except Exception as e:
        return _api_error(500, str(e), "generate_chapter_exception", {"project": project_name, "chapterNumber": chapter_number}, traceback.format_exc())
    finally:
        _release_writing_lock(project_dir)


@app.route("/generate-all-chapters", methods=["POST"])
def generate_all_chapters():
    data = request.get_json(force=True)
    project_name = data.get("project")
    start_chapter = data.get("startChapter")
    end_chapter = data.get("endChapter")
    timeout_seconds = data.get("timeoutSeconds")

    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    settings = _read_json_file(project_dir / "settings.json")
    state = _load_writing_state(project_dir, settings)
    total_chapters = int(state.get("totalChapters") or 0)
    if total_chapters <= 0:
        return jsonify(error="Project settings missing valid totalChapters"), 400

    try:
        start_value = int(start_chapter) if start_chapter is not None else int(state.get("currentChapter") or 1)
        end_value = int(end_chapter) if end_chapter is not None else total_chapters
    except (TypeError, ValueError):
        return _api_error(400, "startChapter and endChapter must be integers", "generate_all_bad_range_type", {"project": project_name, "startChapter": start_chapter, "endChapter": end_chapter})

    if timeout_seconds is not None:
        try:
            timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError):
            return _api_error(400, "timeoutSeconds must be an integer", "generate_all_bad_timeout", {"project": project_name, "timeoutSeconds": timeout_seconds})

    if start_value < 1 or end_value < start_value or end_value > total_chapters:
        return _api_error(400, f"Invalid chapter range: {start_value}..{end_value}", "generate_all_bad_range", {"project": project_name, "startChapter": start_value, "endChapter": end_value, "totalChapters": total_chapters})

    try:
        payload, status_code = _run_chapter_sequence(project_name, start_value, end_value, timeout_seconds=timeout_seconds)
        return jsonify(payload), status_code
    except ValueError as e:
        return _api_error(400, str(e), "generate_all_value_error", {"project": project_name})
    except Exception as e:
        return _api_error(500, str(e), "generate_all_exception", {"project": project_name}, traceback.format_exc())


@app.route("/resume-writing", methods=["POST"])
def resume_writing():
    data = request.get_json(force=True)
    project_name = data.get("project")
    timeout_seconds = data.get("timeoutSeconds")
    if not project_name:
        return jsonify(error="Project required"), 400

    project_dir = DATA_DIR / project_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify(error="Project not found"), 404

    settings = _read_json_file(project_dir / "settings.json")
    state = _load_writing_state(project_dir, settings)
    total_chapters = int(state.get("totalChapters") or 0)
    chapters = state.get("chapters") if isinstance(state.get("chapters"), dict) else {}

    start_chapter = None
    for chapter_number in range(1, total_chapters + 1):
        chapter_state = chapters.get(str(chapter_number), {})
        if chapter_state.get("status") in {"failed", "pending", "in_progress"}:
            start_chapter = chapter_number
            break

    if start_chapter is None:
        return jsonify(status="completed_all", message="All chapters are already completed")

    if timeout_seconds is not None:
        try:
            timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError):
            return _api_error(400, "timeoutSeconds must be an integer", "resume_bad_timeout", {"project": project_name, "timeoutSeconds": timeout_seconds})

    payload, status_code = _run_chapter_sequence(project_name, start_chapter, total_chapters, timeout_seconds=timeout_seconds)
    return jsonify(payload), status_code


if __name__ == "__main__":
    # Run on port 3846 as requested.
    app.run(host="0.0.0.0", port=3846)