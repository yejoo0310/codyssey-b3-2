"""부모 우선 로그와 조상 탐색을 다양한 그래프에서 검증한다."""

import unittest
from datetime import datetime, timezone

from graph import find_ancestors, topological_sort
from models import Commit
from repository import Repository


def make_commit(commit_hash: str, parents: list[str]) -> Commit:
    """테스트에 사용할 커밋을 만든다."""
    return Commit(commit_hash, commit_hash, "Alice", datetime(2026, 10, 16, tzinfo=timezone.utc), parents)


class GraphTests(unittest.TestCase):
    """분기와 여러 부모, 단절된 이력을 함께 확인한다."""

    def setUp(self) -> None:
        """자식을 먼저 저장해 삽입 순서에 의존하지 않는지 확인한다."""
        self.commits = {
            "tip": make_commit("tip", ["merge", "left"]),
            "merge": make_commit("merge", ["left", "right"]),
            "right": make_commit("right", ["root"]),
            "left": make_commit("left", ["root"]),
            "root": make_commit("root", []),
            "separate": make_commit("separate", []),
        }

    def test_topological_log_includes_all_commits_and_respects_every_parent(self) -> None:
        result = topological_sort(self.commits)
        positions = {commit.hash: index for index, commit in enumerate(result)}

        self.assertEqual(len(result), len(self.commits))
        self.assertEqual(set(positions), set(self.commits))
        for commit in result:
            for parent_hash in commit.parents:
                self.assertLess(positions[parent_hash], positions[commit.hash])

    def test_empty_graph_and_single_root(self) -> None:
        self.assertEqual(topological_sort({}), [])
        root = self.commits["root"]
        self.assertEqual(topological_sort({"root": root}), [root])
        self.assertEqual(find_ancestors({"root": root}, "root"), [])

    def test_all_ancestors_are_returned_once_without_start_or_unrelated_roots(self) -> None:
        result = find_ancestors(self.commits, "tip")

        self.assertEqual({commit.hash for commit in result}, {"root", "left", "right", "merge"})
        self.assertEqual(len(result), 4)

    def test_ancestor_search_does_not_follow_children_or_sibling_branches(self) -> None:
        result = find_ancestors(self.commits, "left")

        self.assertEqual([commit.hash for commit in result], ["root"])

    def test_graph_queries_preserve_parent_lists_and_dictionary_order(self) -> None:
        original_order = list(self.commits)
        original_parents = {key: list(commit.parents) for key, commit in self.commits.items()}
        topological_sort(self.commits)
        find_ancestors(self.commits, "tip")

        self.assertEqual(list(self.commits), original_order)
        self.assertEqual({key: commit.parents for key, commit in self.commits.items()}, original_parents)

    def test_deep_history_avoids_recursion_limit(self) -> None:
        commits: dict[str, Commit] = {}
        for index in range(1500):
            parents = [] if index == 0 else [str(index - 1)]
            commits[str(index)] = make_commit(str(index), parents)

        self.assertEqual([commit.hash for commit in topological_sort(commits)], list(commits))
        ancestors = find_ancestors(commits, "1499")
        self.assertEqual(len(ancestors), 1499)
        self.assertEqual({commit.hash for commit in ancestors}, set(commits) - {"1499"})

    def test_unknown_start_commit_is_rejected(self) -> None:
        for commits in ({}, self.commits):
            with self.subTest(empty=not commits):
                with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
                    find_ancestors(commits, "missing")

    def test_missing_parent_is_rejected(self) -> None:
        commits = {"child": make_commit("child", ["missing"])}
        with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
            topological_sort(commits)
        with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
            find_ancestors(commits, "child")

    def test_topological_sort_rejects_cycles_including_disconnected_cycles(self) -> None:
        cases = (
            {"a": make_commit("a", ["a"])},
            {"a": make_commit("a", ["b"]), "b": make_commit("b", ["a"])},
            {"root": make_commit("root", []), "a": make_commit("a", ["b"]), "b": make_commit("b", ["a"])},
        )
        for commits in cases:
            with self.subTest(hashes=list(commits)):
                with self.assertRaisesRegex(ValueError, "^Invalid commit graph: cycle detected$"):
                    topological_sort(commits)


class RepositoryGraphTests(unittest.TestCase):
    """저장소 조회가 그래프 함수와 초기화 검사를 연결하는지 확인한다."""

    def test_graph_queries_require_initialization(self) -> None:
        repository = Repository()
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            repository.get_log()
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            repository.get_ancestors("missing")

    def test_log_includes_other_branches_without_changing_current_position(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        root = repository.create_commit("시작")
        repository.create_branch("feature")
        main_tip = repository.create_commit("메인 작업")
        repository.switch_branch("feature")
        feature_tip = repository.create_commit("기능 작업")

        result = repository.get_log()
        self.assertEqual(result[0], root)
        self.assertEqual({commit.hash for commit in result}, {root.hash, main_tip.hash, feature_tip.hash})
        self.assertEqual(repository.get_ancestors(feature_tip.hash), [root])
        self.assertEqual(repository.current_branch, "feature")
        self.assertEqual(repository.current_commit_hash, feature_tip.hash)
        self.assertEqual(repository.branches["main"], main_tip.hash)

    def test_empty_repository_and_unknown_commit(self) -> None:
        repository = Repository()
        repository.initialize("Alice")

        self.assertEqual(repository.get_log(), [])
        with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
            repository.get_ancestors("missing")
