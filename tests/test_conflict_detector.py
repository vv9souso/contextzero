from contextzero.conflict_detector import detect_conflicts


def test_detects_simple_conflicting_rules():
    files = [
        {"relative_path": "CLAUDE.md", "content": "Always run tests before merging."},
        {"relative_path": "docs/old_handoff.md", "content": "Skip tests for quick patches."},
        {"relative_path": "docs/deploy.md", "content": "Deploy to production after merge."},
        {"relative_path": "docs/staging.md", "content": "Use staging only for deployments."},
    ]

    conflicts = detect_conflicts(files)
    labels = {conflict["label"] for conflict in conflicts}

    assert "skip tests vs run tests" in labels
    assert "production vs staging" in labels
