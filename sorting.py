"""비교 기준을 바꿀 수 있는 안정적인 병합 정렬을 제공한다."""

from models import Commit


def merge_sort(items: list[Commit], key: str) -> list[Commit]:
    """date 또는 author 기준으로 커밋을 안정 정렬한다."""
    if key not in ("date", "author"):
        raise ValueError("Invalid args")
    if len(items) <= 1:
        return items.copy()

    middle = len(items) // 2
    left = merge_sort(items[:middle], key)
    right = merge_sort(items[middle:], key)
    result: list[Commit] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key == "date":
            left_value = left[left_index].timestamp
            right_value = right[right_index].timestamp
        else:
            left_value = left[left_index].author
            right_value = right[right_index].author

        if right_value < left_value:
            result.append(right[right_index])
            right_index += 1
        else:
            # 값이 같으면 왼쪽을 먼저 넣어 기존 순서를 유지한다.
            result.append(left[left_index])
            left_index += 1

    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result
