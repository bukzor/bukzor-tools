from pathlib import Path
from subprocess import run

import pytest

from .roots import (
    find_trash_dirs,
    git_env,
    git_tracks_content,
    is_git_dir,
    scratch_roots,
)


def git(repo: Path, *args: str) -> None:
    run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=git_env())


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "test")
    return path


class DescribeIsGitDir:
    def it_recognizes_a_bare_repository(self, tmp_path: Path):
        run(["git", "init", "-q", "--bare", str(tmp_path)], check=True)
        assert is_git_dir(tmp_path)

    def it_rejects_an_ordinary_directory(self, tmp_path: Path):
        assert not is_git_dir(tmp_path)

    def it_rejects_a_directory_it_may_not_read(self, tmp_path: Path):
        walled = tmp_path / "walled"
        walled.mkdir()
        walled.chmod(0o000)
        try:
            assert not is_git_dir(walled)
        finally:
            walled.chmod(0o700)


class DescribeFindTrashDirs:
    def it_finds_a_nested_trash(self, tmp_path: Path):
        (tmp_path / "a/b/trash").mkdir(parents=True)
        assert list(find_trash_dirs(tmp_path)) == [tmp_path / "a/b/trash"]

    def it_does_not_descend_into_a_trash(self, tmp_path: Path):
        (tmp_path / "trash/trash").mkdir(parents=True)
        assert list(find_trash_dirs(tmp_path)) == [tmp_path / "trash"]

    def it_skips_a_repository_interior(self, tmp_path: Path):
        run(["git", "init", "-q", "--bare", str(tmp_path / "store")], check=True)
        (tmp_path / "store/refs/heads/trash").mkdir(parents=True)
        assert list(find_trash_dirs(tmp_path)) == []

    def it_skips_pruned_names(self, tmp_path: Path):
        (tmp_path / "node_modules/pkg/trash").mkdir(parents=True)
        assert list(find_trash_dirs(tmp_path)) == []


class DescribeGitTracksContent:
    def it_is_false_for_an_untracked_trash(self, tmp_path: Path):
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/scratch.txt").write_text("x")
        assert not git_tracks_content(repo / "trash")

    def it_is_true_for_a_committed_trash(self, tmp_path: Path):
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/vendored.txt").write_text("x")
        git(repo, "add", "trash/vendored.txt")
        git(repo, "commit", "-qm", "vendor")
        assert git_tracks_content(repo / "trash")

    def it_is_true_outside_any_work_tree(self, tmp_path: Path):
        loose = tmp_path / "loose"
        loose.mkdir()
        assert git_tracks_content(loose)

    def it_ignores_an_inherited_repository(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/scratch.txt").write_text("x")
        elsewhere = make_repo(tmp_path / "elsewhere")
        (elsewhere / "tracked.txt").write_text("x")
        git(elsewhere, "add", "tracked.txt")
        git(elsewhere, "commit", "-qm", "content")
        monkeypatch.setenv("GIT_DIR", str(elsewhere / ".git"))
        assert not git_tracks_content(repo / "trash")


class DescribeScratchRoots:
    def it_always_includes_home_tmp(self, tmp_path: Path):
        (tmp_path / "tmp").mkdir()
        assert scratch_roots(tmp_path) == [tmp_path / "tmp"]

    def it_excludes_a_tracked_trash(self, tmp_path: Path):
        (tmp_path / "tmp").mkdir()
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/vendored.txt").write_text("x")
        git(repo, "add", "trash/vendored.txt")
        git(repo, "commit", "-qm", "vendor")
        assert scratch_roots(tmp_path) == [tmp_path / "tmp"]

    def it_includes_an_untracked_trash(self, tmp_path: Path):
        (tmp_path / "tmp").mkdir()
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/scratch.txt").write_text("x")
        assert scratch_roots(tmp_path) == [tmp_path / "tmp", repo / "trash"]
