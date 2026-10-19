"""메모리에서 커밋과 브랜치를 관리한다."""

from datetime import datetime

from graph import find_ancestors, shortest_path, topological_sort
from models import Commit
from search import InvertedIndex
from sorting import merge_sort


class Repository:
    """커밋, 브랜치, 현재 사용자와 hash 발급 순서를 관리한다."""

    def __init__(self) -> None:
        """아직 INIT을 실행하지 않은 빈 저장소를 만든다."""
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        self.current_branch: str | None = None
        self.current_user: str | None = None
        self._commit_counter = 0
        self.index = InvertedIndex()

    def initialize(self, user_name: str) -> None:
        """현재 사용자와 커밋 없는 main 브랜치를 설정한다."""
        if self.current_branch is not None:
            raise ValueError("Repository already initialized")
        if not user_name.strip():
            raise ValueError("Invalid args")

        self.current_user = user_name
        self.branches["main"] = None
        self.current_branch = "main"

    def require_initialized(self) -> str:
        """초기화를 검사하고 현재 브랜치 이름을 반환한다."""
        if self.current_branch is None:
            raise ValueError("Repository not initialized")
        return self.current_branch

    def current_commit_hash(self) -> str | None:
        """현재 브랜치의 커밋 hash를 반환한다. 첫 커밋 전에는 None이다."""
        branch_name = self.require_initialized()
        return self.branches[branch_name]

    def generate_commit_hash(self) -> str:
        """이 저장소 세션에서 중복 없는 hash를 발급한다. 커밋은 생성하지 않는다."""
        self.require_initialized()
        self._commit_counter += 1
        # 6자리는 최소 폭이다. 카운터가 커져도 잘라내거나 다시 시작하지 않는다.
        return f"c{self._commit_counter:06d}"

    def create_commit(self, message: str) -> Commit:
        """현재 커밋을 부모로 새 커밋을 만들고 현재 브랜치를 옮긴다."""
        branch_name = self.require_initialized()
        if not message.strip():
            raise ValueError("Invalid args")

        parent_hash = self.current_commit_hash()
        # 초기화된 저장소에는 작성자가 설정되어 있다.
        assert self.current_user is not None
        commit = Commit(
            hash=self.generate_commit_hash(),
            message=message,
            author=self.current_user,
            timestamp=datetime.now,
            parents=[] if parent_hash is None else [parent_hash],
            branch=branch_name,
        )
        self.commits[commit.hash] = commit
        self.index.add_commit(commit)
        self.branches[branch_name] = commit.hash
        return commit

    def create_branch(self, branch_name: str) -> None:
        """현재 커밋을 가리키는 브랜치를 만든다. 현재 브랜치는 유지한다."""
        self.require_initialized()
        if not branch_name.strip():
            raise ValueError("Invalid args")
        if branch_name in self.branches:
            raise ValueError(f"Branch already exists: {branch_name}")

        # 커밋을 복사하지 않고 같은 hash를 가리킨다.
        self.branches[branch_name] = self.current_commit_hash()

    def switch_branch(self, branch_name: str) -> None:
        """기존 커밋을 그대로 두고 현재 브랜치를 바꾼다."""
        self.require_initialized()
        if not branch_name.strip():
            raise ValueError("Invalid args")
        if branch_name not in self.branches:
            raise ValueError(f"Unknown branch: {branch_name}")

        self.current_branch = branch_name

    def get_log(self, sort_by: str | None = None) -> list[Commit]:
        """기본 로그는 부모 우선, 옵션이 있으면 지정한 기준으로 정렬한다."""
        self.require_initialized()
        if sort_by not in (None, "date", "author"):
            raise ValueError("Invalid args")
        commits = topological_sort(self.commits)
        if sort_by is not None:
            return merge_sort(commits, key=sort_by)
        return commits

    def get_ancestors(self, commit_hash: str) -> list[Commit]:
        """지정한 커밋의 모든 조상을 반환한다."""
        self.require_initialized()
        return find_ancestors(self.commits, commit_hash)

    def get_path(self, start: str, end: str) -> list[str]:
        """두 커밋 사이의 최단 경로를 hash 목록으로 반환한다."""
        self.require_initialized()
        return shortest_path(self.commits, start, end)

    def search_keywords(self, query: str) -> list[Commit]:
        """모든 검색 토큰을 포함하는 커밋을 색인으로 찾는다."""
        self.require_initialized()
        return [self.commits[commit_hash] for commit_hash in self.index.search_keywords(query)]

    def search_author(self, name: str) -> list[Commit]:
        """작성자 이름이 정확히 일치하는 커밋을 색인으로 찾는다."""
        self.require_initialized()
        return [self.commits[commit_hash] for commit_hash in self.index.search_author(name)]
