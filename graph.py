"""커밋 그래프의 로그, 조상 탐색, 최단 경로를 제공한다."""

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

    ready = [commit_hash for commit_hash in commits if remaining_parents[commit_hash] == 0]
    front = 0
    result: list[Commit] = []
    while front < len(ready):
        # 앞 원소를 삭제하지 않고 인덱스만 옮겨 큐처럼 사용한다.
        commit_hash = ready[front]
        front += 1
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


def shortest_path(commits: dict[str, Commit], start: str, end: str) -> list[str]:
    """양방향 최단 경로 중 전체 경로 문자열이 사전순으로 가장 작은 것을 반환한다."""
    for commit_hash in (start, end):
        if commit_hash not in commits:
            raise ValueError(f"Unknown commit: {commit_hash}")
    if start == end:
        return [start]

    neighbors: dict[str, set[str]] = {commit_hash: set() for commit_hash in commits}
    for commit_hash, commit in commits.items():
        for parent_hash in commit.parents:
            if parent_hash not in commits:
                raise ValueError(f"Unknown commit: {parent_hash}")
            neighbors[commit_hash].add(parent_hash)
            neighbors[parent_hash].add(commit_hash)

    # 도착점에서 BFS를 하면 각 커밋에서 도착점까지의 거리를 알 수 있다.
    distances = {end: 0}
    queue = [end]
    front = 0
    visit_order = []
    while front < len(queue):
        current = queue[front]
        front += 1
        visit_order.append(current)
        for neighbor in neighbors[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    if start not in distances:
        return []

    suffixes = {end: end}
    next_hops: dict[str, str] = {}
    # 가까운 커밋부터 최선의 나머지 경로를 정한다. 이웃 순서에는 의존하지 않는다.
    for current in visit_order[1:]:
        best_next = None
        for neighbor in neighbors[current]:
            if distances[neighbor] != distances[current] - 1:
                continue
            if best_next is None or suffixes[neighbor] < suffixes[best_next]:
                best_next = neighbor
        assert best_next is not None
        next_hops[current] = best_next
        suffixes[current] = f"{current}->{suffixes[best_next]}"

    path = [start]
    while path[-1] != end:
        path.append(next_hops[path[-1]])
    return path
