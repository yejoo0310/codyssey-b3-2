"""키워드와 작성자로 커밋을 찾는 역색인을 제공한다."""

from models import Commit


class InvertedIndex:
    """키워드와 작성자별로 커밋 hash 집합을 관리한다."""

    def __init__(self) -> None:
        """검색 기준별로 빈 색인을 준비한다."""
        self.keyword_index: dict[str, set[str]] = {}
        self.author_index: dict[str, set[str]] = {}

    def add_commit(self, commit: Commit) -> None:
        """메시지의 정규화된 토큰과 작성자에 커밋을 등록한다."""
        for keyword in set(commit.message.lower().split()):
            self.keyword_index.setdefault(keyword, set()).add(commit.hash)
        self.author_index.setdefault(commit.author, set()).add(commit.hash)

    def search_keywords(self, query: str) -> set[str]:
        """검색어의 모든 토큰을 포함하는 커밋 hash를 반환한다."""
        keywords = set(query.lower().split())
        if not keywords:
            raise ValueError("Invalid args")

        matches: set[str] | None = None
        for keyword in keywords:
            candidates = self.keyword_index.get(keyword, set())
            if matches is None:
                matches = candidates.copy()
            else:
                matches.intersection_update(candidates)
            if not matches:
                return set()
        # 검색어가 있으므로 적어도 한 토큰의 후보를 확인했다.
        assert matches is not None
        return matches

    def search_author(self, name: str) -> set[str]:
        """이름 전체가 일치하는 작성자의 커밋 hash를 반환한다."""
        if not name.strip():
            raise ValueError("Invalid args")
        # 반환값을 수정해도 원래 색인에 영향을 주지 않도록 복사한다.
        return self.author_index.get(name, set()).copy()
