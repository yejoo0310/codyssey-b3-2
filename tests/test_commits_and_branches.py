"""커밋 생성과 브랜치 분기 시 상태 변화를 확인한다."""

import unittest
from datetime import datetime

from repository import Repository


class CommitAndBranchTests(unittest.TestCase):
    """브랜치 위치와 부모 관계가 올바르게 유지되는지 검증한다."""

    def setUp(self) -> None:
        """각 테스트에 독립된 저장소를 준비한다."""
        self.repository = Repository()
        self.repository.initialize("Alice Kim")

    def test_first_commit_stores_metadata_and_moves_main(self) -> None:
        before = datetime.now()
        commit = self.repository.create_commit("첫 번째 커밋")
        after = datetime.now()

        self.assertEqual(commit.hash, "c000001")
        self.assertEqual(commit.message, "첫 번째 커밋")
        self.assertEqual(commit.author, "Alice Kim")
        self.assertEqual(commit.parents, [])
        self.assertLessEqual(before, commit.timestamp)
        self.assertLessEqual(commit.timestamp, after)
        self.assertIsNone(commit.timestamp.tzinfo)
        self.assertIs(self.repository.commits[commit.hash], commit)
        self.assertEqual(self.repository.current_commit_hash(), commit.hash)
        self.assertEqual(self.repository.branches, {"main": commit.hash})

    def test_next_commit_references_previous_commit_without_changing_it(self) -> None:
        first = self.repository.create_commit("첫 번째 커밋")
        original_metadata = (first.message, first.author, first.timestamp)
        second = self.repository.create_commit("다음 커밋")

        self.assertEqual(second.parents, [first.hash])
        self.assertEqual(first.parents, [])
        self.assertEqual((first.message, first.author, first.timestamp), original_metadata)
        self.assertNotEqual(first.hash, second.hash)
        self.assertEqual(len(self.repository.commits), 2)
        self.assertEqual(self.repository.current_commit_hash(), second.hash)

    def test_new_branch_shares_current_commit_without_switching(self) -> None:
        commit = self.repository.create_commit("분기 지점")
        self.repository.create_branch("feature")

        self.assertEqual(self.repository.current_branch, "main")
        self.assertEqual(self.repository.branches, {"main": commit.hash, "feature": commit.hash})
        self.assertEqual(len(self.repository.commits), 1)

    def test_branch_histories_advance_independently(self) -> None:
        root = self.repository.create_commit("공통 시작점")
        self.repository.create_branch("feature")
        self.repository.switch_branch("feature")
        feature_commit = self.repository.create_commit("로그인 추가")

        self.assertEqual(self.repository.branches["main"], root.hash)
        self.repository.switch_branch("main")
        self.assertEqual(self.repository.current_commit_hash(), root.hash)
        main_commit = self.repository.create_commit("결제 추가")

        self.assertEqual(feature_commit.parents, [root.hash])
        self.assertEqual(main_commit.parents, [root.hash])
        self.assertEqual(root.parents, [])
        self.assertEqual(self.repository.branches["main"], main_commit.hash)
        self.assertEqual(self.repository.branches["feature"], feature_commit.hash)
        self.repository.switch_branch("feature")
        self.assertEqual(self.repository.current_commit_hash(), feature_commit.hash)
        self.assertEqual(len(self.repository.commits), 3)

    def test_empty_branches_can_start_independent_histories(self) -> None:
        self.repository.create_branch("feature")
        self.repository.switch_branch("feature")
        self.assertIsNone(self.repository.current_commit_hash())

        feature_root = self.repository.create_commit("기능 시작")
        self.assertIsNone(self.repository.branches["main"])
        self.repository.switch_branch("main")
        self.assertIsNone(self.repository.current_commit_hash())
        main_root = self.repository.create_commit("메인 시작")

        self.assertEqual(feature_root.parents, [])
        self.assertEqual(main_root.parents, [])
        self.assertEqual(self.repository.branches["feature"], feature_root.hash)
        self.assertNotEqual(feature_root.hash, main_root.hash)

    def test_switching_does_not_create_commits_or_consume_hashes(self) -> None:
        first = self.repository.create_commit("시작")
        self.repository.create_branch("feature")
        self.repository.switch_branch("feature")
        self.repository.switch_branch("main")
        self.repository.switch_branch("main")

        self.assertEqual(self.repository.current_commit_hash(), first.hash)
        self.assertEqual(len(self.repository.commits), 1)
        self.assertEqual(self.repository.create_commit("다음").hash, "c000002")

    def test_operations_before_initialization_leave_repository_empty(self) -> None:
        repository = Repository()
        operations = (
            (repository.create_commit, "시작"),
            (repository.create_branch, "feature"),
            (repository.switch_branch, "main"),
        )
        for operation, argument in operations:
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
                    operation(argument)

        self.assertEqual(repository.commits, {})
        self.assertEqual(repository.branches, {})
        self.assertIsNone(repository.current_branch)
        repository.initialize("Alice")
        self.assertEqual(repository.create_commit("시작").hash, "c000001")

    def test_blank_arguments_do_not_change_existing_state(self) -> None:
        first = self.repository.create_commit("시작")
        operations = (
            self.repository.create_commit,
            self.repository.create_branch,
            self.repository.switch_branch,
        )
        for operation in operations:
            for argument in ("", " ", "\t\n"):
                with self.subTest(operation=operation.__name__, argument=argument):
                    with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                        operation(argument)

        self.assertEqual(self.repository.branches, {"main": first.hash})
        self.assertEqual(self.repository.current_branch, "main")
        self.assertEqual(len(self.repository.commits), 1)
        self.assertEqual(self.repository.create_commit("다음").hash, "c000002")

    def test_duplicate_branch_is_rejected_without_moving_it(self) -> None:
        first = self.repository.create_commit("시작")
        self.repository.create_branch("feature")
        second = self.repository.create_commit("다음")

        for branch_name in ("main", "feature"):
            with self.subTest(branch_name=branch_name):
                with self.assertRaisesRegex(ValueError, f"^Branch already exists: {branch_name}$"):
                    self.repository.create_branch(branch_name)

        self.assertEqual(self.repository.current_branch, "main")
        self.assertEqual(self.repository.branches, {"main": second.hash, "feature": first.hash})
        self.assertEqual(len(self.repository.commits), 2)

    def test_unknown_branch_is_rejected_without_changing_current_branch(self) -> None:
        commit = self.repository.create_commit("시작")

        with self.assertRaisesRegex(ValueError, "^Unknown branch: missing$"):
            self.repository.switch_branch("missing")

        self.assertEqual(self.repository.current_branch, "main")
        self.assertEqual(self.repository.branches, {"main": commit.hash})
        self.assertEqual(len(self.repository.commits), 1)

    def test_message_preserves_case_and_spaces(self) -> None:
        message = "  Add Login Feature  "
        commit = self.repository.create_commit(message)

        self.assertEqual(commit.message, message)

    def test_branch_names_are_case_sensitive_and_allow_spaces(self) -> None:
        for name in ("feature", "Feature", "login feature"):
            self.repository.create_branch(name)

        for name in ("feature", "Feature", "login feature"):
            self.repository.switch_branch(name)
            self.assertEqual(self.repository.current_branch, name)
            self.assertIsNone(self.repository.current_commit_hash())

        self.assertEqual(len(self.repository.branches), 4)
