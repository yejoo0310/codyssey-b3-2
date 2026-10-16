"""병합 정렬의 안정성과 로그 정렬 옵션을 검증한다."""

import ast
import io
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from main import execute_command, main, parse_command
from models import Commit
from repository import Repository
from sorting import merge_sort


class MergeSortTests(unittest.TestCase):
    """입력 형태와 비교 기준에 관계없이 정렬 조건이 유지되는지 확인한다."""

    def test_empty_single_sorted_reverse_and_duplicate_inputs(self) -> None:
        cases = (
            ([], []), ([1], [1]), ([1, 2, 3], [1, 2, 3]),
            ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
            ([3, -1, 3, 0, -1], [-1, -1, 0, 3, 3]),
        )
        for values, expected in cases:
            with self.subTest(values=values):
                original = values.copy()
                result = merge_sort(values, key=lambda value: value)
                self.assertEqual(result, expected)
                self.assertEqual(values, original)
                self.assertIsNot(result, values)

    def test_key_changes_comparison_criterion(self) -> None:
        values = [(3, "a"), (1, "c"), (2, "b")]
        self.assertEqual(merge_sort(values, key=lambda value: value[0]), [(1, "c"), (2, "b"), (3, "a")])
        self.assertEqual(merge_sort(values, key=lambda value: value[1]), [(3, "a"), (2, "b"), (1, "c")])

    def test_equal_keys_preserve_order_across_merge_halves(self) -> None:
        values = [(2, "first"), (1, "second"), (2, "third"), (1, "fourth"), (2, "fifth")]
        self.assertEqual(
            merge_sort(values, key=lambda value: value[0]),
            [(1, "second"), (1, "fourth"), (2, "first"), (2, "third"), (2, "fifth")],
        )

    def test_production_code_does_not_call_standard_sorting_apis(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        for path in project_root.glob("*.py"):
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            self.assertNotEqual(node.func.id, "sorted")
                        if isinstance(node.func, ast.Attribute):
                            self.assertNotIn(node.func.attr, ("sort", "sorted"))


class LogSortingTests(unittest.TestCase):
    """기본 위상 순서와 날짜·작성자 정렬을 구분해 검증한다."""

    def setUp(self) -> None:
        """여러 작성자와 동률, 삽입 순서가 뒤섞인 그래프를 준비한다."""
        self.repository = Repository()
        self.repository.initialize("Tester")
        timestamp = datetime(2026, 10, 17, tzinfo=timezone.utc)
        self.repository.commits = {
            "child": Commit("child", "자식", "Alice", timestamp + timedelta(hours=2), ["root"]),
            "sibling": Commit("sibling", "형제", "Alice", timestamp + timedelta(hours=1), ["root"]),
            "root": Commit("root", "부모", "Bob", timestamp + timedelta(hours=3), []),
            "separate": Commit("separate", "별도 루트", "Bob", timestamp, []),
        }

    def test_default_log_still_keeps_parents_first(self) -> None:
        self.assertEqual([commit.hash for commit in self.repository.get_log()], ["root", "separate", "child", "sibling"])

    def test_author_sort_is_stable_relative_to_topological_log(self) -> None:
        self.assertEqual(
            [commit.hash for commit in self.repository.get_log("author")],
            ["child", "sibling", "root", "separate"],
        )

    def test_date_sort_uses_timestamps_instead_of_parent_or_hash_order(self) -> None:
        self.assertEqual(
            [commit.hash for commit in self.repository.get_log("date")],
            ["separate", "sibling", "child", "root"],
        )

    def test_equal_dates_keep_default_log_order(self) -> None:
        timestamp = datetime(2026, 10, 17, tzinfo=timezone.utc)
        for commit in self.repository.commits.values():
            commit.timestamp = timestamp
        self.assertEqual(self.repository.get_log("date"), self.repository.get_log())

    def test_sorted_log_does_not_change_repository_state(self) -> None:
        original = list(self.repository.commits.items())
        parents = {key: list(commit.parents) for key, commit in original}
        branches = dict(self.repository.branches)
        self.repository.get_log("date")
        self.repository.get_log("author")
        self.assertEqual(list(self.repository.commits.items()), original)
        self.assertEqual({key: commit.parents for key, commit in original}, parents)
        self.assertEqual(self.repository.branches, branches)
        self.assertEqual(self.repository.current_branch, "main")

    def test_empty_logs_and_invalid_sort_criteria(self) -> None:
        repository = Repository()
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            repository.get_log("date")
        repository.initialize("Alice")
        for sort_by in (None, "date", "author"):
            self.assertEqual(repository.get_log(sort_by), [])
        for sort_by in ("", "Date", "message"):
            with self.subTest(sort_by=sort_by):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    repository.get_log(sort_by)

    def test_cli_prints_commits_in_selected_order(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(self.repository, "LOG --sort-by=author"))
        result = output.getvalue()
        order = [line.split()[1] for line in result.splitlines() if line.startswith("commit ")]
        self.assertEqual(order, ["child", "sibling", "root", "separate"])
        self.assertIn("Alice", result)
        self.assertIn("자식", result)


class LogSortCommandTests(unittest.TestCase):
    """옵션 문법과 오류 후 입력 지속, 실제 실행을 확인한다."""

    def test_log_accepts_only_supported_option_forms(self) -> None:
        self.assertEqual(parse_command("lOg"), ("LOG", []))
        for criterion in ("date", "author"):
            self.assertEqual(parse_command(f"lOg --sort-by={criterion}"), ("LOG", [f"--sort-by={criterion}"]))
        for line in ("LOG extra", "LOG --sort-by", "LOG --sort-by=", "LOG --sort-by=message", "LOG --sort-by=Date", "LOG --Sort-by=date", "LOG --sort-by date", "LOG --sort-by=date --sort-by=author"):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(line)

    def test_sort_errors_do_not_stop_repl(self) -> None:
        lines = ["LOG --sort-by=date", "INIT Alice", "LOG --sort-by=wrong", 'COMMIT "시작"', "LOG --sort-by=author", "quit"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=lines):
            with redirect_stdout(output):
                main()
        self.assertIn("Repository not initialized", output.getvalue())
        self.assertIn("Invalid args", output.getvalue())
        self.assertIn("commit c000001 (Alice,", output.getvalue())

    def test_sort_options_run_in_real_process(self) -> None:
        result = subprocess.run(
            [sys.executable, "main.py"],
            input='INIT Alice\nCOMMIT "시작"\nLOG --sort-by=date\nLOG --sort-by=author\nquit\n',
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("commit c000001 (Alice,"), 2)
