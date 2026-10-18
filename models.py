"""커밋 메타데이터를 표현하는 자료구조."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Commit:
    """부모 커밋의 hash 목록을 가진 커밋 기록."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    # default_factory는 커밋마다 별도의 빈 리스트를 만든다.
    parents: list[str] = field(default_factory=list)
    # 브랜치가 이동해도 생성 당시 이름은 유지한다.
    branch: str | None = None
