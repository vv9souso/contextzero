from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .paths import default_brain_db_path, resolve_repo_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    memory_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT NOT NULL,
    tags TEXT NOT NULL,
    source_path TEXT,
    source_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.7,
    stale INTEGER NOT NULL DEFAULT 0,
    superseded_by INTEGER,
    importance_score INTEGER NOT NULL DEFAULT 5,
    FOREIGN KEY(repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    task TEXT,
    created_at TEXT NOT NULL,
    bootstrap TEXT,
    FOREIGN KEY(repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS files_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    mtime REAL,
    estimated_tokens INTEGER,
    stale INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS recall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(repo_id) REFERENCES repos(id)
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else default_brain_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_brain_db(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else default_brain_db_path()
    with _connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    return path


def _repo_id(conn: sqlite3.Connection, repo_path: str | Path) -> int:
    repo = resolve_repo_path(repo_path)
    now = _now()
    row = conn.execute("SELECT id FROM repos WHERE path = ?", (str(repo),)).fetchone()
    if row:
        conn.execute("UPDATE repos SET updated_at = ? WHERE id = ?", (now, row["id"]))
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO repos (name, path, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (repo.name, str(repo), now, now),
    )
    return int(cursor.lastrowid)


def _title_from_text(text: str) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return "Untitled memory"
    first_sentence = clean.split(". ")[0].strip(".")
    return first_sentence[:80]


def remember_memory(
    repo_path: str | Path,
    db_path: str | Path | None = None,
    memory_type: str = "fact",
    text: str = "",
    tags: str = "",
    source_path: str | None = None,
    source_date: str | None = None,
    confidence: float = 0.7,
    stale: bool = False,
    importance_score: int = 5,
) -> int:
    init_brain_db(db_path)
    summary = " ".join(text.strip().split())[:240] or "unknown"
    title = _title_from_text(summary)
    now = _now()
    with _connect(db_path) as conn:
        repo_id = _repo_id(conn, repo_path)
        cursor = conn.execute(
            """
            INSERT INTO memory_cards (
                repo_id, memory_type, title, summary, details, tags, source_path,
                source_date, created_at, updated_at, confidence, stale,
                superseded_by, importance_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                repo_id,
                memory_type,
                title,
                summary,
                text,
                tags,
                source_path,
                source_date,
                now,
                now,
                confidence,
                1 if stale else 0,
                importance_score,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _tokens(text: str) -> set[str]:
    return {token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(token) > 2}


def _score(row: sqlite3.Row, query: str) -> float:
    haystack = " ".join(
        str(row[key] or "")
        for key in ("memory_type", "title", "summary", "details", "tags", "source_path")
    )
    query_tokens = _tokens(query)
    if not query_tokens:
        query_tokens = _tokens(row["tags"] or row["summary"])
    hits = len(query_tokens & _tokens(haystack))
    score = hits * 10 + float(row["confidence"]) * 3 + int(row["importance_score"])
    tag_hits = len(query_tokens & _tokens(row["tags"] or ""))
    score += tag_hits * 8
    if row["stale"]:
        score -= 10
    else:
        score += 5
    return score


def search_memories(
    repo_path: str | Path,
    query: str,
    db_path: str | Path | None = None,
    limit: int = 5,
    include_stale: bool = True,
) -> list[dict]:
    try:
        init_brain_db(db_path)
        with _connect(db_path) as conn:
            repo_id = _repo_id(conn, repo_path)
            rows = conn.execute(
                "SELECT * FROM memory_cards WHERE repo_id = ? ORDER BY updated_at DESC, id DESC",
                (repo_id,),
            ).fetchall()
            scored = []
            for row in rows:
                if row["stale"] and not include_stale:
                    continue
                score = _score(row, query)
                if score <= 0 and query.strip():
                    continue
                item = dict(row)
                item["stale"] = bool(item["stale"])
                item["score"] = score
                scored.append(item)
            scored.sort(key=lambda item: (-item["score"], item["stale"], -item["importance_score"], item["id"]))
            selected = scored[:limit]
            try:
                conn.execute(
                    "INSERT INTO recall_log (repo_id, query, result_count, created_at) VALUES (?, ?, ?, ?)",
                    (repo_id, query, len(selected), _now()),
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass
            return selected
    except sqlite3.OperationalError:
        return []


def extract_candidate_memories(repo_path: str | Path, db_path: str | Path | None = None) -> int:
    from .scanner import scan_repo

    scan = scan_repo(repo_path)
    count = 0
    hints = {
        "decision": ("decision:", "decided", "source of truth"),
        "blocker": ("blocker", "blocked"),
        "todo": ("todo", "next:"),
        "deployment": ("deploy", "deployment"),
        "architecture": ("architecture", "stack"),
        "patch": ("patch", "fixed"),
        "handoff": ("handoff",),
    }
    for file_info in scan["files"]:
        lowered_path = file_info["relative_path"].lower()
        is_stale = any(item["path"] == file_info["relative_path"] for item in scan["stale_files"])
        for line in file_info["content"].splitlines():
            clean = line.strip(" -*\t")
            lowered = clean.lower()
            if len(clean) < 18:
                continue
            for memory_type, patterns in hints.items():
                if any(pattern in lowered or pattern in lowered_path for pattern in patterns):
                    remember_memory(
                        repo_path,
                        db_path,
                        memory_type,
                        clean,
                        tags=memory_type,
                        source_path=file_info["relative_path"],
                        confidence=0.5 if is_stale else 0.7,
                        stale=is_stale,
                        importance_score=4,
                    )
                    count += 1
                    break
    return count


def dump_memory(memories: list[dict]) -> str:
    return json.dumps(memories, indent=2, default=str)
