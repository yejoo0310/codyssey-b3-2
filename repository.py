"""메모리 저장소의 상태와 초기화를 관리한다."""

from models import Commit


class Repository:
    """커밋, 브랜치, 현재 사용자와 hash 발급 순서를 관리한다."""

    def __init__(self) -> None:
        """아직 INIT을 실행하지 않은 빈 저장소를 만든다."""
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        self.current_branch: str | None = None
        self.current_user: str | None = None
        self._commit_counter = 0

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

    @property
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
