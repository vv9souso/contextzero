from contextzero.noise import is_noise_path, task_wants_tests


def test_noise_paths_detected():
    assert is_noise_path("tests/test_x.py")
    assert is_noise_path("examples/messy_repo/README.md")
    assert is_noise_path("src/__pycache__/x.pyc")


def test_real_source_not_noise():
    assert not is_noise_path("src/app/main.py")
    assert not is_noise_path("README.md")


def test_task_intent_for_tests():
    assert task_wants_tests("fix the failing pytest regression")
    assert not task_wants_tests("update the landing copy")
