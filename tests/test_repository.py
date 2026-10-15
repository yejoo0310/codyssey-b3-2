"""저장소 초기화와 hash 발급의 정상·오류 동작을 검증한다."""

import unittest

from repository import Repository


class RepositoryTests(unittest.TestCase):
    """초기화 시 상태 변화와 hash의 유일성을 확인한다."""

    def test_new_repository_is_not_initialized(self) -> None:
        repository = Repository()

        self.assertEqual(repository.commits, {})
        self.assertEqual(repository.branches, {})
        self.assertIsNone(repository.current_branch)
        self.assertIsNone(repository.current_user)

    def test_initialize_sets_user_and_empty_main(self) -> None:
        repository = Repository()
        repository.initialize("Alice Kim")

        self.assertEqual(repository.current_user, "Alice Kim")
        self.assertEqual(repository.current_branch, "main")
        self.assertEqual(repository.branches, {"main": None})
        self.assertIsNone(repository.current_commit_hash)
        self.assertEqual(repository.commits, {})

    def test_access_before_initialization_is_rejected(self) -> None:
        repository = Repository()

        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            repository.require_initialized()
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            _ = repository.current_commit_hash
        with self.assertRaisesRegex(ValueError, "^Repository not initialized$"):
            repository.generate_commit_hash()

        repository.initialize("Alice")
        self.assertEqual(repository.generate_commit_hash(), "c000001")

    def test_reinitialization_preserves_existing_state_and_counter(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        first_hash = repository.generate_commit_hash()
        repository.branches["feature"] = None

        with self.assertRaisesRegex(ValueError, "^Repository already initialized$"):
            repository.initialize("Bob")

        self.assertEqual(repository.current_user, "Alice")
        self.assertEqual(repository.current_branch, "main")
        self.assertEqual(repository.branches, {"main": None, "feature": None})
        self.assertNotEqual(repository.generate_commit_hash(), first_hash)

    def test_blank_user_is_rejected_without_partial_initialization(self) -> None:
        for user_name in ("", " ", "\t\n"):
            with self.subTest(user_name=user_name):
                repository = Repository()
                with self.assertRaisesRegex(ValueError, "^Invalid args$"):
                    repository.initialize(user_name)

                self.assertEqual(repository.branches, {})
                self.assertIsNone(repository.current_branch)
                self.assertIsNone(repository.current_user)
                repository.initialize("Alice")
                self.assertEqual(repository.current_user, "Alice")

    def test_hashes_are_unique_before_commits_are_stored(self) -> None:
        repository = Repository()
        repository.initialize("Alice")

        hashes = [repository.generate_commit_hash() for _ in range(1000)]

        self.assertEqual(len(set(hashes)), 1000)
        self.assertEqual(hashes[0], "c000001")
        self.assertEqual(hashes[-1], "c001000")
        self.assertEqual(repository.commits, {})
        self.assertIsNone(repository.current_commit_hash)

    def test_hash_counter_does_not_wrap_at_six_digits(self) -> None:
        repository = Repository()
        repository.initialize("Alice")
        repository._commit_counter = 999999

        self.assertEqual(repository.generate_commit_hash(), "c1000000")
        self.assertEqual(repository.generate_commit_hash(), "c1000001")

    def test_repository_instances_have_independent_state(self) -> None:
        first = Repository()
        second = Repository()
        first.initialize("Alice")
        first.generate_commit_hash()

        self.assertEqual(second.commits, {})
        self.assertEqual(second.branches, {})
        self.assertIsNone(second.current_user)
        second.initialize("Bob")
        self.assertEqual(second.generate_commit_hash(), "c000001")
        self.assertEqual(first.generate_commit_hash(), "c000002")
