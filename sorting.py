"""비교 기준을 바꿀 수 있는 안정적인 병합 정렬을 제공한다."""

from typing import Any, Callable, TypeVar


T = TypeVar("T")


def merge_sort(items: list[T], key: Callable[[T], Any]) -> list[T]:
    """입력을 바꾸지 않고 key 기준 오름차순으로 안정 정렬한다."""
    if len(items) <= 1:
        return items.copy()

    middle = len(items) // 2
    left = merge_sort(items[:middle], key)
    right = merge_sort(items[middle:], key)
    result: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key(right[right_index]) < key(left[left_index]):
            result.append(right[right_index])
            right_index += 1
        else:
            # 값이 같으면 왼쪽을 먼저 넣어 기존 순서를 유지한다.
            result.append(left[left_index])
            left_index += 1

    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result
