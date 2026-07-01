from pathlib import Path

from contextzero.cli import main


def _numbered_section(output: str, heading: str) -> list[str]:
    lines = output.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    section: list[str] = []
    for line in lines[start:]:
        if not line.strip():
            break
        section.append(line)
    return section


def test_demo_command_runs_without_crashing(capsys):
    exit_code = main(["demo"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ContextZero demo" in output
    assert "Screenshot Summary" in output
    assert "messy_repo_big" in output
    assert "Task:\ndeployment check" in output
    assert "Task:\nlanding page patch" not in output
    assert "- current_state.md: examples/messy_repo_big/.contextzero/current_state.md" in output
    assert "- read_map.json: examples/messy_repo_big/.contextzero/read_map.json" in output
    assert Path.cwd().as_posix() not in output
    assert "/Users/" not in output
    assert "Current production deployment source of truth is docs/production_deploy_current.md." in output


def test_audit_command_runs_without_crashing(capsys):
    exit_code = main(["audit", "examples/messy_repo_big"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ContextZero Audit" in output
    assert "Screenshot Summary" in output
    assert "current_state.md" in output
    assert "read_map.json" in output


def test_start_command_runs_session_bootstrap(capsys):
    exit_code = main(["start", "examples/messy_repo_big", "deployment", "check"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "CONTEXTZERO SESSION BOOTSTRAP" in output
    assert "- none found yet — use `contextzero remember` to store repo decisions." in output
    assert "Read first" in output
    assert "Avoid re-reading unless explicitly needed" in output
    assert "Estimated context avoided" in output
    assert "- source-of-truth files:\n" not in output
    assert "- stale files to avoid:\n" not in output
    assert "docs/production_deploy_current.md" in output

    read_first = _numbered_section(output, "Read first:")
    top_three = "\n".join(read_first[:3])
    assert read_first[0].endswith("docs/production_deploy_current.md")
    assert "docs/current_state_truth.md" in top_three
    assert "docs/patch_notes_long.md" not in top_three
    assert "Read if needed:" in output
    assert "docs/patch_notes_long.md — long history file; use only for background" in output


def test_run_alias_runs_session_bootstrap(capsys):
    exit_code = main(["run", "examples/messy_repo_big", "general", "repo", "work"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "CONTEXTZERO SESSION BOOTSTRAP" in output
    assert "Task:\ngeneral repo work" in output
    assert "Estimated context avoided" in output
