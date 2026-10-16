"""전체 명령 흐름과 조회 간 상태 일관성을 검증한다."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import unittest

from models import Commit
from repository import Repository


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_session(commands: str) -> list[str]:
    """실제 CLI를 실행하고 명령별 출력을 나누어 반환한다."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        input=commands,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=5,
    )
    if result.returncode != 0 or result.stderr:
        raise AssertionError(f"CLI 실행 실패: {result.returncode}\n{result.stderr}")
    return result.stdout.split("mini-git> ")[1:]


def commit_hashes(output: str) -> list[str]:
    """로그 형식의 출력에서 hash만 추출한다."""
    return [line.split()[1] for line in output.splitlines() if line.startswith("commit ")]


class WorkflowTests(unittest.TestCase):
    """초기화부터 탐색·검색·정렬까지 연결해서 확인한다."""

    def test_documented_session_runs_all_required_commands(self) -> None:
        commands = (PROJECT_ROOT / "examples" / "session.txt").read_text()
        output = run_session(commands)

        self.assertEqual(len(output), len(commands.splitlines()))
        self.assertIn("Current user: Alice Kim", output[0])
        self.assertIn("[main c000001] Initial commit", output[1])
        self.assertIn("[feature c000002] Add login feature", output[4])
        self.assertIn("[main c000003] Add payment feature", output[6])
        self.assertEqual(commit_hashes(output[7]), ["c000001", "c000002", "c000003"])
        self.assertEqual(output[8].strip(), "Path: c000002 -> c000001 -> c000003")
        self.assertEqual(commit_hashes(output[9]), ["c000001"])
        self.assertEqual(commit_hashes(output[10]), ["c000002"])
        expected = {"c000001", "c000002", "c000003"}
        self.assertEqual(set(commit_hashes(output[11])), expected)
        self.assertEqual(commit_hashes(output[12]), ["c000001", "c000002", "c000003"])
        self.assertEqual(commit_hashes(output[13]), commit_hashes(output[7]))
        self.assertEqual(output[14], "")

    def test_empty_results_and_errors_recover_in_the_same_session(self) -> None:
        commands = [
            "LOG", "ANCESTORS missing", "PATH a b", "SEARCH login",
            "SEARCH --author=Alice", "LOG --sort-by=date", "LOG --sort-by=author",
            "INIT Alice",
            "LOG", "LOG --sort-by=date", "LOG --sort-by=author", "SEARCH missing", "SEARCH --author=Alice",
            "ANCESTORS missing", "PATH missing missing", "INIT Bob", "BRANCH main", "SWITCH missing",
            'COMMIT "unfinished', 'COMMIT ""', "LOG --sort-by=wrong", "SEARCH --author=", "unknown",
            'COMMIT "Recovered login"', "SEARCH LOGIN", "PATH c000001 c000001", "quit",
        ]
        output = run_session("\n".join(commands) + "\n")

        for block in output[:7]:
            self.assertEqual(block.strip(), "Repository not initialized")
        for block in output[8:13]:
            self.assertEqual(block.strip(), "No commits found.")
        expected_errors = [
            "Unknown commit: missing", "Unknown commit: missing", "Repository already initialized",
            "Branch already exists: main", "Unknown branch: missing", "Invalid args", "Invalid args",
            "Invalid args", "Invalid args", "Unknown command: UNKNOWN",
        ]
        self.assertEqual([block.strip() for block in output[13:23]], expected_errors)
        self.assertIn("[main c000001] Recovered login", output[23])
        self.assertIn("commit c000001 (Alice,", output[24])
        self.assertEqual(output[25].strip(), "Path: c000001")
        self.assertEqual(output[26], "")

    def test_multiple_authors_search_and_sort_share_consistent_data(self) -> None:
        repository = Repository()
        repository.initialize("Tester")
        timestamp = datetime(2026, 10, 17, tzinfo=timezone.utc)
        commits = [
            Commit("root", "Initial shared", "Bob", timestamp, []),
            Commit("left", "Add login shared", "Alice Kim", timestamp + timedelta(hours=2), ["root"]),
            Commit("right", "Fix login shared", "Bob", timestamp + timedelta(hours=1), ["root"]),
            Commit("merge", "Merge shared", "Alice Kim", timestamp + timedelta(hours=3), ["left", "right"]),
        ]
        # 여러 작성자와 두 부모는 저장소 명령을 추가하지 않고 테스트 데이터로 구성한다.
        for commit in commits:
            repository.commits[commit.hash] = commit
            repository.index.add_commit(commit)
        repository.branches["main"] = "merge"
        before = deepcopy((repository.commits, repository.branches, repository.index.keyword_index, repository.index.author_index))

        self.assertEqual([commit.hash for commit in repository.get_log()], ["root", "left", "right", "merge"])
        self.assertEqual([commit.hash for commit in repository.get_log("author")], ["left", "merge", "root", "right"])
        self.assertEqual([commit.hash for commit in repository.get_log("date")], ["root", "right", "left", "merge"])
        self.assertEqual({commit.hash for commit in repository.search_author("Alice Kim")}, {"left", "merge"})
        self.assertEqual({commit.hash for commit in repository.search_author("Bob")}, {"root", "right"})
        self.assertEqual({commit.hash for commit in repository.search_keywords("LOGIN shared")}, {"left", "right"})
        self.assertEqual({commit.hash for commit in repository.get_ancestors("merge")}, {"root", "left", "right"})
        self.assertEqual(repository.get_path("root", "merge"), ["root", "left", "merge"])
        after = (repository.commits, repository.branches, repository.index.keyword_index, repository.index.author_index)
        self.assertEqual(after, before)
        self.assertEqual(repository.current_branch, "main")
        self.assertEqual(repository.current_user, "Tester")

    def test_new_process_starts_with_a_fresh_repository(self) -> None:
        first = run_session('INIT Alice\nCOMMIT "Saved only in memory"\nquit\n')
        second = run_session('LOG\nINIT Bob\nCOMMIT "New session"\nquit\n')
        self.assertIn("[main c000001] Saved only in memory", first[1])
        self.assertEqual(second[0].strip(), "Repository not initialized")
        self.assertIn("[main c000001] New session", second[2])
