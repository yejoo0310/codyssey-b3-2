"""역색인의 갱신과 전체 커밋 순회 없는 검색을 검증한다."""

import io
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

from main import execute_command, main, parse_command
from models import Commit
from repository import Repository
from search import InvertedIndex


class InvertedIndexTests(unittest.TestCase):
    """토큰의 정확한 일치와 작성자 이름의 구분을 확인한다."""

    def setUp(self) -> None:
        """작성자와 메시지가 다른 커밋을 등록한다."""
        self.index = InvertedIndex()
        timestamp = datetime(2026, 10, 17, tzinfo=timezone.utc)
        self.commits = [
            Commit("a", "Add Login login", "Alice Kim", timestamp),
            Commit("b", "Fix LOGIN feature", "Bob", timestamp),
            Commit("c", "Add payment login!", "alice kim", timestamp),
        ]
        for commit in self.commits:
            self.index.add_commit(commit)

    def test_tokens_are_normalized_and_repeated_words_are_deduplicated(self) -> None:
        self.assertEqual(self.index.search_keywords("LOGIN"), {"a", "b"})
        self.assertEqual(self.index.keyword_index["login"], {"a", "b"})
        self.index.add_commit(self.commits[0])
        self.assertEqual(self.index.search_keywords("login login"), {"a", "b"})

    def test_multiple_words_use_intersection_without_changing_indexes(self) -> None:
        self.assertEqual(self.index.search_keywords("  ADD\tlogin  "), {"a"})
        self.assertEqual(self.index.search_keywords("login feature"), {"b"})
        self.assertEqual(self.index.search_keywords("login missing"), set())
        self.assertEqual(self.index.search_keywords("login"), {"a", "b"})
        self.assertEqual(self.index.search_keywords("add"), {"a", "c"})

    def test_keywords_are_whole_tokens_and_punctuation_is_preserved(self) -> None:
        self.assertEqual(self.index.search_keywords("log"), set())
        self.assertEqual(self.index.search_keywords("login!"), {"c"})

    def test_author_names_match_exactly_with_case_and_spaces(self) -> None:
        self.assertEqual(self.index.search_author("Alice Kim"), {"a"})
        self.assertEqual(self.index.search_author("alice kim"), {"c"})
        self.assertEqual(self.index.search_author("Alice"), set())
        self.assertEqual(self.index.search_author(" Alice Kim "), set())
        self.assertEqual(self.index.search_author("missing"), set())

    def test_returned_sets_do_not_expose_internal_indexes(self) -> None:
        self.index.search_keywords("login").clear()
        self.index.search_author("Alice Kim").clear()
        self.assertEqual(self.index.search_keywords("login"), {"a", "b"})
        self.assertEqual(self.index.search_author("Alice Kim"), {"a"})

    def test_blank_queries_are_rejected(self) -> None:
        for query in ("", " ", "\t\n"):
            for search in (self.index.search_keywords, self.index.search_author):
                with self.subTest(query=query, search=search.__name__):
                    with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                        search(query)


class LookupOnlyCommits(dict):
    """전체 순회를 막고 hash 조회만 허용하는 테스트용 딕셔너리."""

    def __iter__(self):
        raise AssertionError("검색 중 전체 커밋을 순회했습니다")

    def values(self):
        raise AssertionError("검색 중 전체 커밋을 순회했습니다")

    def items(self):
        raise AssertionError("검색 중 전체 커밋을 순회했습니다")


class RepositorySearchTests(unittest.TestCase):
    """커밋 생성과 색인 갱신이 연결되는지 확인한다."""

    def test_commits_from_all_branches_are_indexed_without_full_scan(self) -> None:
        repository = Repository()
        repository.initialize("Alice Kim")
        first = repository.create_commit("Add login")
        repository.create_branch("feature")
        repository.switch_branch("feature")
        second = repository.create_commit("Fix login")
        repository.switch_branch("main")
        repository.create_commit("Add payment")
        original_branches = dict(repository.branches)
        # 전체 순회가 가능한 조회를 막아도 검색은 hash 조회만으로 동작해야 한다.
        repository.commits = LookupOnlyCommits(repository.commits)

        self.assertEqual({commit.hash for commit in repository.search_keywords("login")}, {first.hash, second.hash})
        self.assertEqual(repository.search_keywords("fix login"), [second])
        self.assertEqual(len(repository.search_author("Alice Kim")), 3)
        self.assertEqual(repository.branches, original_branches)
        self.assertEqual(repository.current_branch, "main")

    def test_empty_repository_and_missing_queries(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        self.assertEqual(repository.search_keywords("login"), [])
        self.assertEqual(repository.search_author("Alice"), [])
        self.assertEqual(repository.index.keyword_index, {})
        self.assertEqual(repository.index.author_index, {})

    def test_failed_commit_does_not_update_indexes(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        with self.assertRaisesRegex(ValueError, "^Invalid args$"):
            repository.create_commit(" ")
        self.assertEqual(repository.index.keyword_index, {})
        self.assertEqual(repository.index.author_index, {})
        self.assertEqual(repository.create_commit("Valid").hash, "c000001")

    def test_search_requires_initialization_and_instances_have_separate_indexes(self) -> None:
        first = Repository()
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            first.search_keywords("login")
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            first.search_author("Alice")
        first.initialize("Alice")
        first.create_commit("login")
        second = Repository()
        second.initialize("Bob")
        self.assertEqual(second.search_keywords("login"), [])
        self.assertEqual(second.search_author("Alice"), [])


class SearchCommandTests(unittest.TestCase):
    """검색 옵션의 문법과 결과 출력을 검증한다."""

    def test_search_accepts_quoted_keywords_and_author_option(self) -> None:
        self.assertEqual(parse_command('sEaRcH "Add Login"'), ("SEARCH", ["Add Login"]))
        self.assertEqual(parse_command('SEARCH --author="Alice Kim"'), ("SEARCH", ["--author=Alice Kim"]))

    def test_invalid_search_arguments_and_options_are_rejected(self) -> None:
        lines = ("SEARCH", "SEARCH one two", 'SEARCH ""', "SEARCH --author", "SEARCH --author=", 'SEARCH --author=" "', "SEARCH --author Alice", "SEARCH --Author=Alice", "SEARCH --unknown=x")
        for line in lines:
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    parse_command(line)

    def test_search_prints_matching_metadata_and_empty_results(self) -> None:
        repository = Repository()
        repository.initialize("Alice Kim")
        commit = repository.create_commit("Add Login")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_command(repository, 'SEARCH "add login"'))
            execute_command(repository, 'SEARCH --author="Alice Kim"')
            execute_command(repository, "SEARCH missing")
        result = output.getvalue()
        self.assertEqual(result.count(f"commit {commit.hash} (Alice Kim,"), 2)
        self.assertEqual(result.count("Add Login"), 2)
        self.assertIn("No commits found.", result)

    def test_search_errors_do_not_stop_repl(self) -> None:
        lines = ["SEARCH login", "SEARCH --author=Alice", "INIT Alice", "SEARCH --author=", 'COMMIT "Add login"', "SEARCH LOGIN", "quit"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=lines):
            with redirect_stdout(output):
                main()
        result = output.getvalue()
        self.assertEqual(result.count("Repository not initialized"), 2)
        self.assertIn("Invalid args", result)
        self.assertIn("commit c000001 (Alice,", result)

    def test_search_runs_in_real_process(self) -> None:
        result = subprocess.run(
            [sys.executable, "main.py"],
            input='INIT "Alice Kim"\nCOMMIT "Add Login"\nSEARCH "add login"\nSEARCH --author="Alice Kim"\nquit\n',
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("commit c000001 (Alice Kim,"), 2)
