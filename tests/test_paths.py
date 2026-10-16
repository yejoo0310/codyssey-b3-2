"""양방향 최단 경로와 전체 문자열 기준의 동률 처리를 검증한다."""

import io
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

from graph import shortest_path
from main import execute_command, main, parse_command
from models import Commit
from repository import Repository


def make_graph(parents: dict[str, list[str]]) -> dict[str, Commit]:
    """부모 관계만 지정해 테스트 그래프를 만든다."""
    timestamp = datetime(2026, 10, 16, tzinfo=timezone.utc)
    return {key: Commit(key, key, "Alice", timestamp, values) for key, values in parents.items()}


class ShortestPathTests(unittest.TestCase):
    """최소 간선 수와 사전순 조건을 따로 확인한다."""

    def test_paths_work_in_both_directions_and_between_siblings(self) -> None:
        commits = make_graph({"root": [], "left": ["root"], "right": ["root"], "tip": ["left"]})
        self.assertEqual(shortest_path(commits, "root", "tip"), ["root", "left", "tip"])
        self.assertEqual(shortest_path(commits, "tip", "root"), ["tip", "left", "root"])
        self.assertEqual(shortest_path(commits, "left", "right"), ["left", "root", "right"])

    def test_same_commit_has_zero_edges(self) -> None:
        commits = make_graph({"root": []})
        self.assertEqual(shortest_path(commits, "root", "root"), ["root"])

    def test_disconnected_commits_have_no_path(self) -> None:
        commits = make_graph({"root": [], "child": ["root"], "separate": []})
        self.assertEqual(shortest_path(commits, "child", "separate"), [])

    def test_unknown_start_and_end_are_rejected(self) -> None:
        commits = make_graph({"root": []})
        for start, end in (("missing", "root"), ("root", "missing"), ("missing", "missing")):
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
                    shortest_path(commits, start, end)
        with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
            shortest_path({}, "missing", "other")

    def test_shorter_path_wins_before_lexicographic_order(self) -> None:
        commits = make_graph({"end": [], "a": ["b"], "b": ["end"], "z": ["end"], "start": ["a", "z"]})
        self.assertEqual(shortest_path(commits, "start", "end"), ["start", "z", "end"])

    def test_equal_paths_choose_lexicographically_smallest_string(self) -> None:
        commits = make_graph({"root": [], "z": ["root"], "a": ["root"], "merge": ["z", "a"]})
        self.assertEqual(shortest_path(commits, "root", "merge"), ["root", "a", "merge"])
        self.assertEqual(shortest_path(commits, "merge", "root"), ["merge", "a", "root"])

    def test_tie_can_be_decided_after_a_shared_prefix(self) -> None:
        commits = make_graph({"end": [], "z": ["end"], "a": ["end"], "middle": ["z", "a"], "start": ["middle"]})
        self.assertEqual(shortest_path(commits, "start", "end"), ["start", "middle", "a", "end"])

    def test_full_string_order_can_differ_from_hash_order(self) -> None:
        commits = make_graph({"end": [], "a": ["end"], "a!": ["end"], "start": ["a", "a!"]})
        # a < a!이지만 a!->end < a->end이므로 전체 문자열을 비교해야 한다.
        self.assertEqual(shortest_path(commits, "start", "end"), ["start", "a!", "end"])

    def test_storage_and_parent_order_do_not_affect_ties(self) -> None:
        relations = {"end": [], "b": ["end"], "a": ["end"], "start": ["b", "a"]}
        first = make_graph(relations)
        second = make_graph({key: list(reversed(values)) for key, values in reversed(list(relations.items()))})
        self.assertEqual(shortest_path(first, "start", "end"), ["start", "a", "end"])
        self.assertEqual(shortest_path(second, "start", "end"), ["start", "a", "end"])

    def test_missing_parent_is_rejected(self) -> None:
        commits = make_graph({"start": ["missing"], "end": []})
        with self.assertRaisesRegex(ValueError, "^Unknown commit: missing$"):
            shortest_path(commits, "start", "end")

    def test_long_history_uses_iteration(self) -> None:
        commits = make_graph({str(index): [] if index == 0 else [str(index - 1)] for index in range(1500)})
        self.assertEqual(shortest_path(commits, "0", "1499"), [str(index) for index in range(1500)])

    def test_query_preserves_graph_and_branch_positions(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        root = repository.create_commit("시작")
        repository.create_branch("feature")
        child = repository.create_commit("다음")
        original_parents = {key: list(commit.parents) for key, commit in repository.commits.items()}
        original_branches = dict(repository.branches)

        self.assertEqual(repository.get_path(root.hash, child.hash), [root.hash, child.hash])
        self.assertEqual(repository.current_branch, "main")
        self.assertEqual(repository.branches, original_branches)
        self.assertEqual({key: commit.parents for key, commit in repository.commits.items()}, original_parents)

    def test_repository_query_requires_initialization(self) -> None:
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            Repository().get_path("start", "end")


class PathCommandTests(unittest.TestCase):
    """PATH의 인자 검사와 출력, 오류 후 입력 지속을 확인한다."""

    def test_path_requires_exactly_two_nonempty_arguments(self) -> None:
        self.assertEqual(parse_command("pAtH c000001 c000002"), ("PATH", ["c000001", "c000002"]))
        for line in ("PATH", "PATH a", "PATH a b c", 'PATH "" b', 'PATH a " "'):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(line)

    def test_path_output_same_commit_and_no_path(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        repository.create_branch("separate")
        first = repository.create_commit("시작")
        second = repository.create_commit("다음")
        repository.switch_branch("separate")
        separate = repository.create_commit("독립 이력")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(repository, f"PATH {second.hash} {first.hash}"))
            execute_command(repository, f"PATH {first.hash} {first.hash}")
            execute_command(repository, f"PATH {first.hash} {separate.hash}")
        self.assertEqual(output.getvalue(), "Path: c000002 -> c000001\nPath: c000001\nNo path\n")

    def test_path_errors_do_not_stop_repl(self) -> None:
        lines = ["PATH a b", "INIT Alice", 'COMMIT "시작"', "PATH missing c000001", "PATH c000001 missing", "PATH c000001", "PATH c000001 c000001", "quit"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=lines):
            with redirect_stdout(output):
                main()
        for message in ("Repository not initialized", "Unknown commit: missing", "Invalid args", "Path: c000001"):
            self.assertIn(message, output.getvalue())

    def test_path_runs_in_real_process(self) -> None:
        result = subprocess.run(
            [sys.executable, "main.py"],
            input='INIT Alice\nCOMMIT "시작"\nCOMMIT "다음"\nPATH c000002 c000001\nquit\n',
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("Path: c000002 -> c000001", result.stdout)
