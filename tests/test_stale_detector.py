from contextzero.stale_detector import detect_stale_files


def test_detects_stale_files_by_name_and_content():
    files = [
        {
            "relative_path": "docs/old_handoff.md",
            "content": "Current owner: unknown",
            "modified_days_ago": 5,
        },
        {
            "relative_path": "docs/deployment.md",
            "content": "This plan is deprecated and no longer current.",
            "modified_days_ago": 5,
        },
    ]

    stale = detect_stale_files(files)
    paths = {item["path"] for item in stale}

    assert "docs/old_handoff.md" in paths
    assert "docs/deployment.md" in paths
