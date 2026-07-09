import subprocess

from contextzero.gitfiles import relevant_files, is_git_repo


def _init(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)


def test_is_git_repo_false_for_plain_dir(tmp_path):
    assert is_git_repo(tmp_path) is False


def test_relevant_files_includes_new_and_staged_excludes_ignored(tmp_path):
    _init(tmp_path)
    (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True)
    (tmp_path / "feature_new.md").write_text("wip", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("secret.md\n", encoding="utf-8")
    (tmp_path / "secret.md").write_text("nope", encoding="utf-8")
    files = {p.as_posix() for p in relevant_files(tmp_path)}
    assert "README.md" in files
    assert "feature_new.md" in files
    assert "secret.md" not in files


def test_relevant_files_none_when_not_git(tmp_path):
    assert relevant_files(tmp_path) is None
