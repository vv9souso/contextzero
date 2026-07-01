from contextzero.duplicate_detector import detect_duplicate_instructions


def test_detects_duplicate_instruction_blocks():
    files = [
        {
            "relative_path": "CLAUDE.md",
            "content": "Run pytest before reporting done.\nKeep token savings estimates labeled.\n",
        },
        {
            "relative_path": "AGENTS.md",
            "content": "Run pytest before reporting done.\nKeep token savings estimates labeled.\n",
        },
    ]

    duplicates = detect_duplicate_instructions(files)

    assert duplicates
    assert "Run pytest before reporting done" in duplicates[0]["text"]
    assert {"CLAUDE.md", "AGENTS.md"} <= set(duplicates[0]["locations"])
