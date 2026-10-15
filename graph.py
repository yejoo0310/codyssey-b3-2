"""커밋 그래프의 부모 우선 정렬과 조상 탐색을 제공한다."""

from collections import deque

from models import Commit


def topological_sort(commits: dict[str, Commit]) -> list[Commit]:
    """모든 부모가 자식보다 먼저 나오도록 Kahn 알고리즘으로 정렬한다."""
    remaining_parents: dict[str, int] = {}
    children: dict[str, list[str]] = {commit_hash: [] for commit_hash in commits}
    for commit_hash, commit in commits.items():
        parents = set(commit.parents)
        remaining_parents[commit_hash] = len(parents)
        for parent_hash in parents:
            if parent_hash not in commits:
                raise ValueError(f"Unknown commit: {parent_hash}")
            children[parent_hash].append(commit_hash)

    ready = deque(commit_hash for commit_hash in commits if remaining_parents[commit_hash] == 0)
    result: list[Commit] = []
    while ready:
        commit_hash = ready.popleft()
        result.append(commits[commit_hash])
        for child_hash in children[commit_hash]:
            remaining_parents[child_hash] -= 1
            # 모든 부모를 출력한 자식만 다음 처리 대상으로 넣는다.
            if remaining_parents[child_hash] == 0:
                ready.append(child_hash)

    if len(result) != len(commits):
        raise ValueError("Invalid commit graph: cycle detected")
    return result


def find_ancestors(commits: dict[str, Commit], commit_hash: str) -> list[Commit]:
    """부모 방향으로 탐색해 시작 커밋을 제외한 조상을 중복 없이 반환한다."""
    if commit_hash not in commits:
        raise ValueError(f"Unknown commit: {commit_hash}")

    stack = [commit_hash]
    visited = {commit_hash}
    result: list[Commit] = []
    while stack:
        current_hash = stack.pop()
        for parent_hash in commits[current_hash].parents:
            if parent_hash not in commits:
                raise ValueError(f"Unknown commit: {parent_hash}")
            if parent_hash in visited:
                continue
            # 발견할 때 방문 표시를 해 공통 조상을 여러 번 쌓지 않는다.
            visited.add(parent_hash)
            result.append(commits[parent_hash])
            stack.append(parent_hash)
    return result
