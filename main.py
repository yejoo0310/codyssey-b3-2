"""Mini Git의 명령을 읽고 실행한다."""

import shlex

from models import Commit
from repository import Repository


def parse_command(line: str) -> tuple[str, list[str]]:
    """따옴표를 처리하고 명령 이름과 인자 개수를 검사한다."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        raise ValueError("Invalid args") from None

    if not tokens:
        return "", []

    command = tokens[0].upper()
    arguments = tokens[1:]
    argument_counts = {
        "INIT": 1, "COMMIT": 1, "BRANCH": 1, "SWITCH": 1,
        "LOG": 0, "ANCESTORS": 1, "PATH": 2, "SEARCH": 1, "EXIT": 0, "QUIT": 0,
    }
    if not command:
        raise ValueError("Invalid args")
    if command not in argument_counts:
        raise ValueError(f"Unknown command: {command}")
    if len(arguments) != argument_counts[command]:
        raise ValueError("Invalid args")
    if any(not argument.strip() for argument in arguments):
        raise ValueError("Invalid args")
    if command == "SEARCH" and arguments[0].startswith("--"):
        if not arguments[0].startswith("--author=") or not arguments[0][len("--author="):].strip():
            raise ValueError("Invalid args")
    return command, arguments


def print_commits(commits: list[Commit]) -> None:
    """커밋의 hash, 작성자, 시각, 메시지를 출력한다."""
    if not commits:
        print("No commits found.")
        return
    for commit in commits:
        timestamp = commit.timestamp.isoformat(sep=" ", timespec="seconds")
        print(f"commit {commit.hash} ({commit.author}, {timestamp})")
        print(commit.message)


def execute_command(repository: Repository, line: str) -> bool:
    """한 줄을 실행하고, 입력을 계속 받을지 반환한다."""
    command, arguments = parse_command(line)
    if command in ("EXIT", "QUIT"):
        return False
    if not command:
        return True
    if command == "LOG":
        print_commits(repository.get_log())
        return True

    argument = arguments[0]
    if command == "INIT":
        repository.initialize(argument)
        print("Initialized repository.")
        print(f"Current branch: {repository.current_branch}")
        print(f"Current user: {repository.current_user}")
    elif command == "COMMIT":
        commit = repository.create_commit(argument)
        print(f"[{repository.current_branch} {commit.hash}] {commit.message}")
    elif command == "BRANCH":
        repository.create_branch(argument)
        print(f"Created branch: {argument}")
    elif command == "SWITCH":
        repository.switch_branch(argument)
        print(f"Switched to branch: {argument}")
    elif command == "ANCESTORS":
        print_commits(repository.get_ancestors(argument))
    elif command == "PATH":
        path = repository.get_path(arguments[0], arguments[1])
        print("Path: " + " -> ".join(path) if path else "No path")
    elif command == "SEARCH":
        if argument.startswith("--author="):
            print_commits(repository.search_author(argument[len("--author="):]))
        else:
            print_commits(repository.search_keywords(argument))
    return True


def main() -> None:
    """오류를 출력한 뒤 다음 명령을 받는 입력 반복문을 실행한다."""
    repository = Repository()
    while True:
        try:
            line = input("mini-git> ")
        except (EOFError, KeyboardInterrupt):
            # 입력이 끝나거나 Ctrl+C를 누르면 줄을 바꾸고 종료한다.
            print()
            break

        try:
            if not execute_command(repository, line):
                break
        except ValueError as error:
            print(error)


if __name__ == "__main__":
    main()
