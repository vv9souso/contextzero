from contextzero.token_estimator import estimate_tokens, estimate_file_tokens


def test_estimates_tokens_from_characters():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2


def test_estimates_tokens_from_file(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("a" * 17, encoding="utf-8")

    assert estimate_file_tokens(path) == 5
