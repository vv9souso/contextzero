from __future__ import annotations

import argparse
import json
from pathlib import Path

from .brain import default_brain_db_path, extract_candidate_memories, init_brain_db, remember_memory
from .capsule_builder import write_current_state
from .claude_installer import install_claude_support
from .doctor import format_doctor, run_doctor
from .read_map_builder import write_read_map
from .recall import format_recall
from .reports import screenshot_summary, terminal_summary, write_report, write_scan_artifacts
from .scanner import scan_repo
from .session_bootstrap import build_session_bootstrap, write_session_bootstrap


def _task_text(parts: list[str] | None) -> str:
    return " ".join(parts or []).strip()


def _print_install_message() -> None:
    print(
        """ContextZero installed.

Powered by Caveman Brain.

Daily use:
1. Open Claude Code in this repo.
2. Type /contextzero
3. Start your task.

ContextZero will:
- refresh the current-state capsule
- recall relevant repo memories
- warn about stale docs
- tell Claude what to read first
- keep old junk out of the session"""
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contextzero", description="Local context hygiene for AI coding agents.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("repo_path", nargs="?", default=".")
    init.add_argument("--install-claude", action="store_true")
    init.add_argument("--brain", action="store_true")

    scan = sub.add_parser("scan")
    scan.add_argument("repo_path", nargs="?", default=".")

    report = sub.add_parser("report")
    report.add_argument("repo_path", nargs="?", default=".")

    audit = sub.add_parser("audit")
    audit.add_argument("repo_path", nargs="?", default=".")

    capsule = sub.add_parser("capsule")
    capsule.add_argument("repo_path", nargs="?", default=".")

    read_map = sub.add_parser("map")
    read_map.add_argument("repo_path", nargs="?", default=".")

    session = sub.add_parser("session-bootstrap")
    session.add_argument("repo_path", nargs="?", default=".")
    session.add_argument("task", nargs="*")

    start = sub.add_parser("start")
    start.add_argument("repo_path", nargs="?", default=".")
    start.add_argument("task", nargs="*")

    run = sub.add_parser("run")
    run.add_argument("repo_path", nargs="?", default=".")
    run.add_argument("task", nargs="*")

    fresh = sub.add_parser("fresh-start")
    fresh.add_argument("repo_path", nargs="?", default=".")
    fresh.add_argument("task", nargs="*")

    remember = sub.add_parser("remember")
    remember.add_argument("repo_path", nargs="?", default=".")
    remember.add_argument("--type", required=True, dest="memory_type")
    remember.add_argument("--text", required=True)
    remember.add_argument("--tags", default="")
    remember.add_argument("--stale", action="store_true")

    recall = sub.add_parser("recall")
    recall.add_argument("repo_path", nargs="?", default=".")
    recall.add_argument("query", nargs="*")

    update_brain = sub.add_parser("update-brain")
    update_brain.add_argument("repo_path", nargs="?", default=".")

    doctor = sub.add_parser("doctor")
    doctor.add_argument("repo_path", nargs="?", default=".")
    doctor.add_argument("--brain", action="store_true")

    sub.add_parser("demo")
    return parser


def _examples_path() -> Path:
    cwd_example = Path("examples") / "messy_repo_big"
    if cwd_example.exists():
        return cwd_example
    return Path(__file__).resolve().parents[1] / "examples" / "messy_repo_big"


def _demo_display_text(text: str) -> str:
    cwd = Path.cwd().resolve().as_posix()
    return text.replace(f"{cwd}/", "").replace(cwd, ".")


def _run_audit(repo_path: str | Path) -> str:
    scan = scan_repo(repo_path)
    write_scan_artifacts(repo_path, scan)
    current_state = write_current_state(repo_path)
    read_map = write_read_map(repo_path)
    report = write_report(repo_path)
    return "\n".join(
        [
            "ContextZero Audit",
            "",
            screenshot_summary(repo_path, scan),
            "",
            "Artifacts written:",
            f"- current_state.md: {Path(current_state).as_posix()}",
            f"- read_map.json: {Path(read_map).as_posix()}",
            f"- contextzero-report.md: {Path(report).as_posix()}",
            f"- contextzero-report.json: {Path(report).with_suffix('.json').as_posix()}",
            f"- token_waste_estimate.json: {(Path(report).parent / 'token_waste_estimate.json').as_posix()}",
            f"- stale_files.json: {(Path(report).parent / 'stale_files.json').as_posix()}",
            f"- duplicates.json: {(Path(report).parent / 'duplicates.json').as_posix()}",
            f"- conflicts.json: {(Path(report).parent / 'conflicts.json').as_posix()}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        write_report(args.repo_path)
        write_current_state(args.repo_path)
        write_read_map(args.repo_path)
        if args.brain:
            init_brain_db(default_brain_db_path())
        if args.install_claude:
            install_claude_support(args.repo_path)
        _print_install_message()
        return 0

    if args.command == "scan":
        result = scan_repo(args.repo_path)
        write_scan_artifacts(args.repo_path, result)
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0

    if args.command == "report":
        path = write_report(args.repo_path)
        print(terminal_summary(args.repo_path))
        print(f"Report written: {path}")
        return 0

    if args.command == "audit":
        print(_run_audit(args.repo_path))
        return 0

    if args.command == "capsule":
        path = write_current_state(args.repo_path)
        print(path.read_text(encoding="utf-8"))
        return 0

    if args.command == "map":
        path = write_read_map(args.repo_path)
        print(path)
        return 0

    if args.command == "session-bootstrap":
        output = build_session_bootstrap(args.repo_path, _task_text(args.task))
        write_session_bootstrap(args.repo_path, _task_text(args.task))
        print(output)
        return 0

    if args.command in {"start", "run"}:
        task = _task_text(args.task) or "general repo work"
        output = build_session_bootstrap(args.repo_path, task)
        write_session_bootstrap(args.repo_path, task)
        print(output)
        return 0

    if args.command == "fresh-start":
        output = build_session_bootstrap(args.repo_path, _task_text(args.task), fresh_start=True)
        write_session_bootstrap(args.repo_path, _task_text(args.task), fresh_start=True)
        print(output)
        return 0

    if args.command == "remember":
        memory_id = remember_memory(
            args.repo_path,
            default_brain_db_path(),
            args.memory_type,
            args.text,
            args.tags,
            stale=args.stale,
        )
        print(f"Remembered memory card {memory_id}.")
        return 0

    if args.command == "recall":
        print(format_recall(args.repo_path, _task_text(args.query), db_path=default_brain_db_path()))
        return 0

    if args.command == "update-brain":
        count = extract_candidate_memories(args.repo_path, default_brain_db_path())
        print(f"Stored {count} candidate memory cards.")
        return 0

    if args.command == "doctor":
        print(format_doctor(run_doctor(args.repo_path, brain_enabled=args.brain, db_path=default_brain_db_path())))
        return 0

    if args.command == "demo":
        repo = _examples_path()
        demo_db = repo / ".contextzero" / "demo-brain.db"
        if demo_db.exists():
            demo_db.unlink()
        init_brain_db(demo_db)
        remember_memory(
            repo,
            demo_db,
            "deployment",
            "Current production deployment source of truth is docs/production_deploy_current.md.",
            "deployment,current",
            source_path="docs/production_deploy_current.md",
            confidence=0.95,
            importance_score=9,
        )
        remember_memory(
            repo,
            demo_db,
            "deployment",
            "Old deployment docs are archived and should not drive new work.",
            "deployment,archive",
            source_path="docs/production_deploy_old.md",
            confidence=0.9,
            stale=True,
            importance_score=8,
        )
        print("ContextZero demo")
        print(f"Repo: {Path(repo).as_posix()}")
        scan = scan_repo(repo)
        write_scan_artifacts(repo, scan)
        write_report(repo)
        output = build_session_bootstrap(repo, "deployment check", db_path=demo_db)
        write_session_bootstrap(repo, "deployment check", db_path=demo_db)
        print("")
        print(_demo_display_text(screenshot_summary(repo, scan)))
        print("")
        print(_demo_display_text(output))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
