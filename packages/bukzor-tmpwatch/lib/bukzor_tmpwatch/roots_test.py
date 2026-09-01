from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from subprocess import run

import pytest

from . import roots as roots_module
from .config_test import DEFAULTS
from .roots import (
    find_dirs_named,
    git_env,
    git_tracks_content,
    is_git_dir,
    outermost,
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


def make_scratch_trash(parent: Path) -> Path:
    """An untracked trash/ inside a repository -- the shape that gets swept."""
    repo = make_repo(parent)
    (repo / "trash").mkdir()
    (repo / "trash/scratch.txt").write_text("x")
    return repo / "trash"


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


class DescribeFindDirsNamed:
    def it_finds_a_nested_match(self, tmp_path: Path):
        (tmp_path / "a/b/trash").mkdir(parents=True)
        assert list(find_dirs_named(tmp_path, "trash", DEFAULTS.prune)) == [
            tmp_path / "a/b/trash"
        ]

    def it_does_not_descend_into_a_match(self, tmp_path: Path):
        (tmp_path / "trash/trash").mkdir(parents=True)
        assert list(find_dirs_named(tmp_path, "trash", DEFAULTS.prune)) == [
            tmp_path / "trash"
        ]

    def it_skips_a_repository_interior(self, tmp_path: Path):
        run(["git", "init", "-q", "--bare", str(tmp_path / "store")], check=True)
        (tmp_path / "store/refs/heads/trash").mkdir(parents=True)
        assert list(find_dirs_named(tmp_path, "trash", DEFAULTS.prune)) == []

    def it_skips_pruned_names(self, tmp_path: Path):
        (tmp_path / "node_modules/pkg/trash").mkdir(parents=True)
        assert list(find_dirs_named(tmp_path, "trash", DEFAULTS.prune)) == []

    def it_looks_for_the_name_it_is_given(self, tmp_path: Path):
        (tmp_path / "junk").mkdir()
        (tmp_path / "trash").mkdir()
        assert list(find_dirs_named(tmp_path, "junk", DEFAULTS.prune)) == [
            tmp_path / "junk"
        ]

    def it_descends_into_a_pruned_name_when_nothing_is_pruned(self, tmp_path: Path):
        (tmp_path / "node_modules/pkg/trash").mkdir(parents=True)
        assert list(find_dirs_named(tmp_path, "trash", ())) == [
            tmp_path / "node_modules/pkg/trash"
        ]


class DescribeGitTracksContent:
    def it_is_false_for_an_untracked_trash(self, tmp_path: Path):
        assert not git_tracks_content(make_scratch_trash(tmp_path / "repo"))

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
        trash = make_scratch_trash(tmp_path / "repo")
        elsewhere = make_repo(tmp_path / "elsewhere")
        (elsewhere / "tracked.txt").write_text("x")
        git(elsewhere, "add", "tracked.txt")
        git(elsewhere, "commit", "-qm", "content")
        monkeypatch.setenv("GIT_DIR", str(elsewhere / ".git"))
        assert not git_tracks_content(trash)


class DescribeOutermost:
    def it_drops_a_root_that_lies_inside_another(self, tmp_path: Path):
        """Sweeping the outer one moves the inner one aside mid-run."""
        outer = tmp_path / "tmp"
        assert outermost([outer, outer / "project/trash"]) == [outer]

    def it_keeps_siblings(self, tmp_path: Path):
        roots = [tmp_path / "a", tmp_path / "b"]
        assert outermost(roots) == roots

    def it_keeps_a_root_that_only_shares_a_prefix(self, tmp_path: Path):
        roots = [tmp_path / "tmp", tmp_path / "tmp2"]
        assert outermost(roots) == roots


class DescribeScratchRoots:
    def it_starts_with_the_configured_roots(self, tmp_path: Path):
        config = replace(DEFAULTS, roots=(tmp_path / "scratch",))
        assert scratch_roots(tmp_path, config) == [tmp_path / "scratch"]

    def it_adds_an_untracked_trash(self, tmp_path: Path):
        trash = make_scratch_trash(tmp_path / "repo")
        assert scratch_roots(tmp_path, DEFAULTS) == [trash]

    def it_excludes_a_tracked_trash(self, tmp_path: Path):
        repo = make_repo(tmp_path / "repo")
        (repo / "trash").mkdir()
        (repo / "trash/vendored.txt").write_text("x")
        git(repo, "add", "trash/vendored.txt")
        git(repo, "commit", "-qm", "vendor")
        assert scratch_roots(tmp_path, DEFAULTS) == []

    def it_searches_for_the_configured_name(self, tmp_path: Path):
        repo = make_repo(tmp_path / "repo")
        (repo / "junk").mkdir()
        (repo / "junk/scratch.txt").write_text("x")
        config = replace(DEFAULTS, trash_dir="junk")
        assert scratch_roots(tmp_path, config) == [repo / "junk"]

    def it_drops_a_trash_that_lies_inside_a_configured_root(self, tmp_path: Path):
        make_scratch_trash(tmp_path / "scratch/repo")
        config = replace(DEFAULTS, roots=(tmp_path / "scratch",))
        assert scratch_roots(tmp_path, config) == [tmp_path / "scratch"]

    def it_searches_at_all_only_when_a_name_is_configured(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """An emptied trash-dir switches off the walk, not merely its results."""

        def refuse(*args: object) -> Iterator[Path]:
            raise AssertionError(args)

        monkeypatch.setattr(roots_module, "find_dirs_named", refuse)
        config = replace(DEFAULTS, roots=(tmp_path / "scratch",), trash_dir="")
        assert scratch_roots(tmp_path, config) == [tmp_path / "scratch"]
