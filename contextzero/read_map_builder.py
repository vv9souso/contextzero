from __future__ import annotations

import json
from pathlib import Path

from .paths import artifact_path, relative_to_repo, resolve_repo_path, write_text
from .scanner import EXCLUDED_DIRS
from .stale_detector import detect_stale_files


READ_MAP_CATEGORIES = [
    "frontend",
    "backend",
    "auth",
    "billing",
    "deployment",
    "tests",
    "docs",
    "database",
    "analytics",
    "design",
    "support",
    "unknown",
]

SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def _source_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            parts = path.relative_to(repo).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS or part == ".pytest_cache" for part in parts):
            continue
        if path.name in {"package-lock.json"}:
            continue
        files.append(path)
    return sorted(files)


def _category_for(path: str, content: str) -> list[str]:
    lowered = f"{path}\n{content[:2000]}".lower()
    categories: list[str] = []
    checks = {
        "frontend": ("frontend", "component", "react", "vite", "css", "landing", "homepage", "hero", "creator", "join", "page", "cta", "nav", "ui"),
        "backend": ("backend", "api", "server", "fastapi", "express", "route"),
        "auth": ("auth", "login", "oauth", "session", "token"),
        "billing": ("billing", "stripe", "invoice", "subscription", "payment"),
        "deployment": ("deploy", "docker", "release", "production", "staging", "vercel"),
        "tests": ("test", "pytest", "spec", "unittest"),
        "docs": ("readme", "product.md", "docs/", "claude.md", "agents.md", "install", "roadmap"),
        "database": ("database", "sqlite", "postgres", "migration", "schema", ".db"),
        "analytics": ("analytics", "metrics", "event", "tracking"),
        "design": ("design", "style", "brand", "figma", "wireframe"),
        "support": ("support", "faq", "help", "troubleshoot"),
    }
    for category, hints in checks.items():
        if any(hint in lowered for hint in hints):
            categories.append(category)
    return categories or ["unknown"]


def build_read_map(repo_path: str | Path = ".") -> dict:
    repo = resolve_repo_path(repo_path)
    records = []
    for path in _source_files(repo):
        content = path.read_text(encoding="utf-8", errors="ignore")
        records.append({"relative_path": relative_to_repo(path, repo), "content": content})

    stale_paths = {item["path"] for item in detect_stale_files(records)}
    read_map = {
        category: {
            "recommended_files": [],
            "avoid_unless_needed": [],
            "reason": f"Files likely relevant to {category} tasks.",
        }
        for category in READ_MAP_CATEGORIES
    }

    for record in records:
        rel_path = record["relative_path"]
        categories = _category_for(rel_path, record["content"])
        for category in categories:
            target = (
                read_map[category]["avoid_unless_needed"]
                if rel_path in stale_paths
                else read_map[category]["recommended_files"]
            )
            if rel_path not in target:
                target.append(rel_path)

    for category, data in read_map.items():
        data["recommended_files"] = data["recommended_files"][:10]
        data["avoid_unless_needed"] = data["avoid_unless_needed"][:10]
        if not data["recommended_files"] and category != "unknown":
            data["reason"] = f"No clear {category} source files detected."
    return read_map


def write_read_map(repo_path: str | Path = ".") -> Path:
    text = json.dumps(build_read_map(repo_path), indent=2, sort_keys=True)
    return write_text(artifact_path(repo_path, "read_map"), text + "\n")
