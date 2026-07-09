from __future__ import annotations

NOISE_DIR_PARTS = {"tests", "test", "examples", "example", "fixtures",
                   "fixture", "demo", "demos", "__pycache__", "node_modules",
                   "vendor", "third_party", "dist", "build"}

# task terms that legitimately want test/example files surfaced
TEST_INTENT_TERMS = {"test", "tests", "pytest", "fixture", "fixtures",
                     "regression", "coverage", "spec", "specs"}


def is_noise_path(rel_path: str) -> bool:
    parts = rel_path.lower().replace("\\", "/").split("/")
    return any(part in NOISE_DIR_PARTS for part in parts)


def task_wants_tests(task: str) -> bool:
    tokens = {t for t in "".join(c.lower() if c.isalnum() else " " for c in task).split()}
    return bool(tokens & TEST_INTENT_TERMS)
