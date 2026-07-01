from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contextzero_codex_skill_exists_and_mentions_trigger() -> None:
    skill_path = ROOT / ".agents" / "skills" / "contextzero" / "SKILL.md"

    assert skill_path.exists()

    skill_text = skill_path.read_text(encoding="utf-8")

    assert 'description: Use this skill when the user says "run contextzero"' in skill_text
    assert "run contextzero" in skill_text
    assert "run contextzero means session bootstrap, not scan" in skill_text
    assert 'contextzero start . "general repo work"' in skill_text
    assert "Do not edit files during this step." in skill_text


def test_codex_trigger_docs_are_present() -> None:
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    prompts_text = (ROOT / "PROMPTS.md").read_text(encoding="utf-8")

    assert "## ContextZero Trigger Rule" in agents_text
    assert 'Default command:\n`contextzero start . "general repo work"`' in agents_text
    assert "Do not use `contextzero scan` unless the user explicitly asks for scan/audit/report." in agents_text
    assert "run contextzero" in readme_text
    assert "Daily Codex use:" in readme_text
    assert 'contextzero start . "general repo work"' in readme_text
    assert "For audit/report:" in readme_text
    assert "contextzero audit ." in readme_text
    assert "Simplest Codex prompt:" in prompts_text
    assert "Task-specific Codex prompt:" in prompts_text
    assert (
        'If Codex runs `contextzero scan` after the user says only "run contextzero", that is wrong.'
        in prompts_text
    )
