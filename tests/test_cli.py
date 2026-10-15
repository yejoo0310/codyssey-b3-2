"""명령 파싱과 반복 입력의 정상·오류 흐름을 검증한다."""

import io
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from main import execute_command, main, parse_command
from repository import Repository


class CommandParsingTests(unittest.TestCase):
    """명령 이름만 정규화하고 문자열 인자는 보존하는지 확인한다."""

    def test_command_case_is_ignored_and_argument_case_is_preserved(self) -> None:
        self.assertEqual(parse_command('cOmMiT "Add Login Feature"'), ("COMMIT", ["Add Login Feature"]))

    def test_quotes_preserve_spaces_and_allow_single_quotes(self) -> None:
        self.assertEqual(parse_command('INIT "  Alice Kim  "'), ("INIT", ["  Alice Kim  "]))
        self.assertEqual(parse_command("BRANCH 'login feature'"), ("BRANCH", ["login feature"]))
        self.assertEqual(parse_command('COMMIT "Alice\'s feature"'), ("COMMIT", ["Alice's feature"]))

    def test_empty_lines_are_ignored(self) -> None:
        for line in ("", " ", "\t"):
            with self.subTest(line=line):
                self.assertEqual(parse_command(line), ("", []))

    def test_missing_extra_and_blank_arguments_are_rejected(self) -> None:
        for command in ("INIT", "COMMIT", "BRANCH", "SWITCH"):
            for suffix in ("", " one two", ' ""', ' "   "'):
                with self.subTest(command=command, suffix=suffix):
                    with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                        parse_command(command + suffix)

    def test_malformed_quotes_and_empty_command_are_rejected(self) -> None:
        for line in ('COMMIT "unfinished', "INIT 'unfinished", '"" Alice', '""'):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(line)

    def test_exit_commands_do_not_accept_arguments(self) -> None:
        for command in ("exit", "QUIT"):
            with self.subTest(command=command):
                self.assertEqual(parse_command(command), (command.upper(), []))
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(command + " extra")

    def test_unknown_commands_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "^Unknown command: MISSING$"):
            parse_command("missing argument")


class CommandExecutionTests(unittest.TestCase):
    """입력한 명령이 저장소 상태와 출력에 반영되는지 확인한다."""

    def test_branch_workflow_with_quoted_names_and_messages(self) -> None:
        repository = Repository()
        output = io.StringIO()
        lines = (
            'init "Alice Kim"',
            'commit "Initial commit"',
            'branch "Login Feature"',
            'switch "Login Feature"',
            'commit "Add Login"',
            'switch main',
            'commit "Add Payment"',
        )
        with redirect_stdout(output):
            for line in lines:
                self.assertTrue(execute_command(repository, line))

        self.assertEqual(repository.current_user, "Alice Kim")
        self.assertEqual(repository.branches, {"main": "c000003", "Login Feature": "c000002"})
        self.assertEqual(repository.commits["c000002"].parents, ["c000001"])
        self.assertEqual(repository.commits["c000003"].parents, ["c000001"])
        self.assertEqual(repository.commits["c000002"].message, "Add Login")
        self.assertIn("Current user: Alice Kim", output.getvalue())
        self.assertIn("Created branch: Login Feature", output.getvalue())
        self.assertIn("Switched to branch: Login Feature", output.getvalue())
        self.assertIn("[main c000003] Add Payment", output.getvalue())

    def test_exit_and_quit_work_before_initialization(self) -> None:
        for line in ("exit", "ExIt", "quit", "QUIT"):
            with self.subTest(line=line):
                repository = Repository()
                self.assertFalse(execute_command(repository, line))
                self.assertEqual(repository.branches, {})

    def test_blank_input_has_no_output_or_side_effects(self) -> None:
        repository = Repository()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(repository, "  "))
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(repository.branches, {})

    def test_invalid_commit_does_not_consume_hash(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        for line in ('COMMIT "unterminated', 'COMMIT one two', 'COMMIT ""'):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    execute_command(repository, line)
        self.assertEqual(repository.commits, {})
        self.assertEqual(repository.create_commit("valid").hash, "c000001")


class ReplTests(unittest.TestCase):
    """실패한 명령 뒤에도 입력을 받고 정상 종료하는지 확인한다."""

    def test_errors_do_not_stop_repl_or_reset_repository(self) -> None:
        lines = [
            'commit "Before init"',
            'init "Alice Kim"',
            'init Bob',
            'commit "unfinished',
            'commit one two',
            'missing',
            'branch main',
            'switch missing',
            'exit extra',
            '',
            'commit "Still working"',
            'quit',
        ]
        output = io.StringIO()
        with patch("builtins.input", side_effect=lines) as read_line:
            with redirect_stdout(output):
                main()

        result = output.getvalue()
        for message in (
            "Repository not initialized", "Repository already initialized",
            "Invalid args", "Unknown command: MISSING", "Branch already exists: main",
            "Unknown branch: missing", "[main c000001] Still working",
        ):
            self.assertIn(message, result)
        self.assertEqual(read_line.call_count, len(lines))
        read_line.assert_called_with("mini-git> ")

    def test_exit_stops_before_reading_another_command(self) -> None:
        for command in ("exit", "quit"):
            with self.subTest(command=command):
                with patch("builtins.input", side_effect=[command, "INIT Alice"]) as read_line:
                    main()
                self.assertEqual(read_line.call_count, 1)

    def test_eof_and_keyboard_interrupt_exit_without_traceback(self) -> None:
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error):
                output = io.StringIO()
                with patch("builtins.input", side_effect=error):
                    with redirect_stdout(output):
                        main()
                self.assertEqual(output.getvalue(), "\n")

    def test_entry_point_runs_in_a_real_process(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "main.py"],
            input='INIT "Alice Kim"\nCOMMIT "Initial commit"\n',
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("mini-git> ", result.stdout)
        self.assertIn("Current user: Alice Kim", result.stdout)
        self.assertIn("[main c000001] Initial commit", result.stdout)


class GraphCommandTests(unittest.TestCase):
    """로그와 조상 탐색의 입력 규칙과 출력을 확인한다."""

    def test_graph_command_arguments(self) -> None:
        self.assertEqual(parse_command("lOg"), ("LOG", []))
        self.assertEqual(parse_command("aNcEsToRs c000001"), ("ANCESTORS", ["c000001"]))
        for line in ("LOG extra", "LOG --sort-by=date", "ANCESTORS", "ANCESTORS one two", 'ANCESTORS ""'):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(line)

    def test_log_and_ancestors_print_metadata_in_parent_first_order(self) -> None:
        repository = Repository()
        repository.initialize("Alice Kim")
        root = repository.create_commit("시작")
        repository.create_branch("feature")
        child = repository.create_commit("메인 작업")
        repository.switch_branch("feature")
        feature = repository.create_commit("기능 작업")

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(repository, "LOG"))
        result = output.getvalue()
        self.assertLess(result.index(f"commit {root.hash}"), result.index(f"commit {child.hash}"))
        self.assertLess(result.index(f"commit {root.hash}"), result.index(f"commit {feature.hash}"))
        self.assertIn("Alice Kim", result)
        self.assertIn(root.timestamp.isoformat(sep=" ", timespec="seconds"), result)
        self.assertIn("메인 작업", result)
        self.assertIn("기능 작업", result)

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(repository, f"ANCESTORS {feature.hash}"))
        self.assertIn(f"commit {root.hash}", output.getvalue())
        self.assertNotIn(f"commit {feature.hash}", output.getvalue())
        self.assertNotIn(f"commit {child.hash}", output.getvalue())

    def test_empty_log_and_root_ancestors_print_empty_result(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        output = io.StringIO()
        with redirect_stdout(output):
            execute_command(repository, "LOG")
            root = repository.create_commit("시작")
            execute_command(repository, f"ANCESTORS {root.hash}")

        self.assertEqual(output.getvalue(), "No commits found.\nNo commits found.\n")

    def test_graph_errors_do_not_stop_repl(self) -> None:
        lines = ["LOG", "ANCESTORS missing", "INIT Alice", "ANCESTORS missing", 'COMMIT "시작"', "LOG", "quit"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=lines):
            with redirect_stdout(output):
                main()

        result = output.getvalue()
        self.assertEqual(result.count("Repository not initialized"), 2)
        self.assertIn("Unknown commit: missing", result)
        self.assertIn("commit c000001 (Alice,", result)

    def test_graph_commands_run_in_real_process(self) -> None:
        result = subprocess.run(
            [sys.executable, "main.py"],
            input='INIT Alice\nCOMMIT "시작"\nCOMMIT "다음"\nLOG\nANCESTORS c000002\nquit\n',
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("commit c000001 (Alice,"), 2)
        self.assertEqual(result.stdout.count("commit c000002 (Alice,"), 1)
