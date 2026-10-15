"""커밋의 부모 관계 표현을 검증한다."""

import unittest
from datetime import datetime, timezone

from models import Commit


class CommitTests(unittest.TestCase):
    """루트와 여러 부모 커밋을 표현할 수 있는지 확인한다."""

    def test_root_commits_do_not_share_parent_lists(self) -> None:
        timestamp = datetime(2026, 10, 15, tzinfo=timezone.utc)
        first = Commit("c000001", "Initial commit", "Alice", timestamp)
        second = Commit("c000002", "Another root", "Bob", timestamp)

        self.assertEqual(first.parents, [])
        self.assertIsNot(first.parents, second.parents)
        first.parents.append("test-parent")
        self.assertEqual(second.parents, [])

    def test_commit_can_represent_multiple_parents(self) -> None:
        timestamp = datetime(2026, 10, 15, tzinfo=timezone.utc)
        commit = Commit(
            hash="c000003",
            message="Merge feature",
            author="Alice",
            timestamp=timestamp,
            parents=["c000001", "c000002"],
        )

        self.assertEqual(commit.parents, ["c000001", "c000002"])
        self.assertEqual(commit.timestamp, timestamp)
