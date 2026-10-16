# Mini Git

커밋과 브랜치의 관계를 메모리에 저장하는 Python CLI 학습 프로젝트입니다.
커밋 그래프를 만들고 탐색·검색·정렬 기능을 직접 구현하며 Git의 내부 구조와 알고리즘을 공부합니다.

현재는 **Phase 5: 최단 경로 탐색**까지 완료했습니다.
반복 입력 CLI에서 `INIT`, `COMMIT`, `BRANCH`, `SWITCH`, `LOG`, `ANCESTORS`, `PATH`, `exit`, `quit`를 사용할 수 있습니다.
`SEARCH`와 로그 정렬 옵션은 이후 Phase의 구현 목표입니다.

## 개발 환경과 실행

- Python 3.10 이상
- 실행 엔트리 포인트: `main.py`
- 프로젝트 디렉터리에서 실행합니다.

```bash
python main.py
```

실행 후 `mini-git>` 프롬프트에서 명령을 입력하고 `exit` 또는 `quit`로 종료합니다.
EOF(일반적인 터미널에서 Ctrl+D)나 Ctrl+C로도 종료할 수 있습니다.
`python` 명령이 없다면 `python3 main.py`로 실행합니다.
별도 외부 패키지 없이 Python 표준 라이브러리와 기본 자료형을 사용합니다.

### Phase 3 CLI 실행해 보기

```text
mini-git> init "Alice Kim"
Initialized repository.
Current branch: main
Current user: Alice Kim
mini-git> commit "Initial commit"
[main c000001] Initial commit
mini-git> branch "Login Feature"
Created branch: Login Feature
mini-git> switch "Login Feature"
Switched to branch: Login Feature
mini-git> COMMIT "Add Login"
[Login Feature c000002] Add Login
mini-git> switch missing
Unknown branch: missing
mini-git> switch main
Switched to branch: main
mini-git> commit "Add Payment"
[main c000003] Add Payment
mini-git> quit
```

명령어 이름의 대소문자는 구분하지 않고, 사용자명·브랜치명·메시지는 원문을 유지합니다.
공백이 있는 인자는 큰따옴표나 작은따옴표로 감쌉니다.
따옴표가 닫히지 않거나 인자 수가 맞지 않으면 `Invalid args`를 출력합니다.
빈 입력은 무시하며, 오류가 발생해도 같은 저장소 상태로 다음 명령을 받습니다.
`exit`, `quit`는 초기화 전에도 사용할 수 있지만 인자를 붙이면 오류가 발생합니다.
아직 구현하지 않은 명령도 `Unknown command: <COMMAND>`로 처리합니다.

`main.py`의 `parse_command()`는 입력을 분리하고 형식을 검사합니다.
`execute_command()`는 저장소 메서드를 호출하고 결과를 출력하며, 종료 명령이면 `False`를 반환합니다.
`main()`은 하나의 저장소를 유지하면서 입력과 실행을 반복하고 오류를 처리합니다.

### Phase 4 로그와 조상 탐색 실행해 보기

새로 실행한 CLI에서 아래 명령을 입력합니다. 시각은 실행 시점에 따라 달라지며 UTC로 표시합니다.

```text
mini-git> INIT Alice
Initialized repository.
Current branch: main
Current user: Alice
mini-git> COMMIT "Initial commit"
[main c000001] Initial commit
mini-git> BRANCH feature
Created branch: feature
mini-git> SWITCH feature
Switched to branch: feature
mini-git> COMMIT "Add login"
[feature c000002] Add login
mini-git> SWITCH main
Switched to branch: main
mini-git> COMMIT "Add payment"
[main c000003] Add payment
mini-git> LOG
commit c000001 (Alice, 2026-10-16 00:00:00+00:00)
Initial commit
commit c000002 (Alice, 2026-10-16 00:01:00+00:00)
Add login
commit c000003 (Alice, 2026-10-16 00:02:00+00:00)
Add payment
mini-git> ANCESTORS c000003
commit c000001 (Alice, 2026-10-16 00:00:00+00:00)
Initial commit
mini-git> ANCESTORS c000001
No commits found.
mini-git> ANCESTORS missing
Unknown commit: missing
```

`LOG`는 현재 브랜치와 관계없이 저장소 전체 커밋을 출력합니다.
부모가 반드시 자식보다 먼저 나오며, 선후 관계가 없는 형제 커밋의 순서는 자유입니다.
빈 저장소의 로그나 루트 커밋의 조상 목록은 `No commits found.`를 출력합니다.
`ANCESTORS`는 부모 방향으로만 탐색하고 시작 커밋 자신과 다른 가지의 커밋은 포함하지 않습니다.
결과 순서는 자유이며 같은 조상은 한 번만 출력합니다.
두 조회 명령은 커밋, 부모 관계, 브랜치 위치를 변경하지 않습니다.
초기화 전에는 두 명령 모두 `Repository not initialized` 오류를 출력합니다.
`LOG --sort-by=...`는 Phase 7에서 추가하므로 현재는 `Invalid args`로 처리합니다.

#### 알고리즘 구조

`graph.py`에 입력·출력과 분리한 두 함수를 구현했습니다.
`Repository.get_log()`와 `Repository.get_ancestors(hash)`가 초기화 검사 후 이 함수를 호출하고,
CLI의 `print_commits()`가 반환된 커밋 목록을 출력합니다.

| 함수 | 방법 | 시간복잡도 | 추가 공간 |
| --- | --- | --- | --- |
| `topological_sort(commits)` | Kahn 위상 정렬 | `O(V + E)` | `O(V + E)` |
| `find_ancestors(commits, hash)` | 스택을 사용하는 부모 방향 DFS | `O(Va + Ea)` | `O(Va)` |

`V`는 전체 커밋 수, `E`는 부모 연결 수입니다.
`Va`, `Ea`는 시작 커밋과 그 조상에서 방문한 커밋·부모 연결 수입니다.
복잡도는 딕셔너리·집합의 평균 조회 비용을 기준으로 합니다.

위상 정렬은 부모 수와 부모에서 자식을 찾는 목록을 만든 뒤, 남은 부모 수가 0인 커밋부터 큐로 처리합니다.
조상 탐색은 스택과 방문 집합을 사용하며, 발견할 때 방문 표시를 해 공통 조상을 중복 처리하지 않습니다.
그래프에서 없는 부모를 참조하면 `Unknown commit: <hash>` 오류가 발생합니다.
위상 정렬 중 모든 커밋을 처리하지 못하면 순환으로 판단하고 `Invalid commit graph: cycle detected` 오류가 발생합니다.
조상 탐색의 방문 집합은 중복과 무한 반복을 막지만, 순환 검증 기능을 대신하지는 않습니다.

### Phase 5 최단 경로 실행해 보기

위 Phase 4 예제의 분기 이력에서 이어서 실행할 수 있습니다.

```text
mini-git> PATH c000002 c000003
Path: c000002 -> c000001 -> c000003
mini-git> PATH c000001 c000003
Path: c000001 -> c000003
mini-git> PATH c000003 c000001
Path: c000003 -> c000001
mini-git> PATH c000001 c000001
Path: c000001
mini-git> PATH c000001 missing
Unknown commit: missing
```

`PATH <start> <end>`는 부모 연결을 양방향으로 봅니다. 따라서 부모뿐 아니라 자식 쪽으로도 이동하며,
형제 커밋 사이를 공통 부모를 거쳐 탐색할 수 있습니다. 간선 수가 가장 적은 경로를 선택하고,
연결이 없으면 `No path`를 출력합니다. 같은 커밋을 지정하면 간선 수가 0인 경로를 반환합니다.
명령에는 정확히 두 hash가 필요하고, 조회해도 커밋이나 브랜치 위치는 바뀌지 않습니다.

연결되지 않은 이력은 첫 커밋 전에 브랜치를 나누어 확인할 수 있습니다. 새 CLI 세션에서 실행합니다.

```text
INIT Alice
BRANCH separate
COMMIT "Main root"
SWITCH separate
COMMIT "Separate root"
PATH c000001 c000002
```

마지막 명령의 결과는 `No path`입니다.

#### 최단 거리와 동률 처리

`graph.shortest_path(commits, start, end)`가 hash 목록을 반환하고,
`Repository.get_path(start, end)`가 초기화 검사 후 호출합니다.

1. 부모와 자식을 모두 이웃으로 등록해 무방향 인접 목록을 만듭니다.
2. 도착점에서 BFS를 수행해 각 커밋에서 도착점까지의 최소 간선 수를 구합니다.
3. 도착점에 가까운 커밋부터, 거리가 정확히 1 줄어드는 이웃만 후보로 삼습니다.
4. 후보의 도착점까지 전체 경로 문자열을 비교해 가장 작은 경로와 다음 이동 위치를 저장합니다.
5. 출발점에서 다음 이동 위치를 따라가 경로를 복원합니다.

거리가 매번 1씩 줄어들므로 복원한 경로는 반드시 최단 경로입니다.
동률 비교에는 공백 없는 `hash1->hash2->...` 문자열을 사용하고, 출력할 때만 화살표 양옆에 공백을 넣습니다.
전체 문자열을 직접 비교하므로 표준 정렬 API나 별도의 이웃 정렬은 필요하지 않습니다.
여러 최단 경로가 있는 그래프는 테스트 데이터로 구성하며, MERGE 명령은 아직 구현하지 않았습니다.

BFS와 인접 목록 구성은 `O(V + E)`입니다. 동률 선택에는 경로 문자열의 생성·비교 비용이 추가됩니다.
`L`을 저장하는 경로 문자열의 최대 길이라고 하면 전체 시간은 최악 `O((V + E) × L)`,
추가 공간은 `O(V + E + V × L)`입니다. 문자열을 저장하므로 전체 PATH 비용을 BFS 비용만으로 설명할 수는 없습니다.

### Phase 1 실행해 보기

프로젝트 디렉터리에서 `python`을 실행한 뒤 아래 코드를 입력할 수 있습니다.
초기화만 한 상태에는 커밋이 없으므로 현재 커밋은 `None`입니다.

```python
from repository import Repository

repository = Repository()              # 저장소 객체 생성. 아직 INIT 전 상태
repository.initialize("Alice Kim")     # 사용자와 빈 main 브랜치 설정
print(repository.current_user)         # Alice Kim
print(repository.current_branch)       # main
print(repository.current_commit_hash)  # None
print(repository.generate_commit_hash())  # c000001
print(repository.generate_commit_hash())  # c000002
```

hash 발급은 식별자를 예약하는 동작으로, 커밋을 만들거나 브랜치를 이동하지 않습니다.
증가 카운터는 저장소 인스턴스마다 별도로 유지되며, 발급한 번호를 재사용하지 않습니다.
6자리 표시는 최소 폭이므로 999999를 넘어도 잘라내거나 처음으로 돌아가지 않습니다.
`initialize()`를 다시 호출하면 `ValueError("Repository already initialized")`가 발생합니다.
초기화 전에 현재 커밋을 조회하거나 hash를 발급하면 `ValueError("Repository not initialized")`가 발생합니다.
`require_initialized()`는 이후 저장소 명령에서도 재사용할 초기화 검사 메서드입니다.

### Phase 2 실행해 보기

새 저장소에서 커밋을 만들고 브랜치를 나눠봅니다.
`create_commit()`은 생성한 `Commit` 객체를 반환하고, 브랜치 생성·전환 메서드는 반환값 없이 상태를 변경합니다.

```python
from repository import Repository

repository = Repository()
repository.initialize("Alice")
root = repository.create_commit("Initial commit")
repository.create_branch("feature")  # 같은 커밋을 가리키는 브랜치만 추가
print(repository.current_branch)     # main

repository.switch_branch("feature")
feature = repository.create_commit("Add login")
print(repository.branches["main"])   # c000001: main은 분기 지점에 남아 있음

repository.switch_branch("main")
payment = repository.create_commit("Add payment")

print(root.parents)                        # []
print(feature.parents)                     # ['c000001']
print(payment.parents)                     # ['c000001']
print(repository.branches)                 # {'main': 'c000003', 'feature': 'c000002'}
print(repository.current_commit_hash)      # c000003
print(len(repository.commits))             # 3
```

커밋을 생성하면 현재 커밋의 hash를 부모로 저장하고, 현재 브랜치만 새 커밋으로 옮깁니다.
작성자는 초기화할 때 설정한 사용자이며 시각은 UTC 기준으로 기록합니다.
메시지는 빈 값이나 공백만 있는 값을 거부하고, 유효한 메시지의 대소문자와 공백은 그대로 보존합니다.
브랜치 생성과 전환은 커밋을 만들거나 hash를 발급하지 않습니다.
커밋이 없는 브랜치에서 첫 커밋을 만들면 다른 브랜치의 상태와 관계없이 부모가 없는 커밋이 됩니다.

없는 브랜치 전환은 `Unknown branch: <name>`, 중복 브랜치 생성은
`Branch already exists: <name>` 오류를 발생시키며 기존 상태를 유지합니다.
역색인 갱신은 Phase 6에서 커밋 생성 흐름에 추가합니다.

### 테스트 실행

Python 표준 라이브러리 `unittest`를 사용합니다.

```bash
python -m unittest discover -s tests -v
```

Phase 1 테스트는 부모 리스트의 독립성, 여러 부모 표현, 초기 상태, 빈 사용자명,
재초기화 시 기존 상태 보존, 초기화 전 접근, hash 유일성·자리수 경계, 저장소 간 독립성을 확인합니다.
Phase 2 테스트는 커밋 메타데이터와 부모 관계, 브랜치별 독립적인 이동, 빈 브랜치,
잘못된 인자·중복 이름·없는 브랜치로 실패했을 때의 상태 보존을 확인합니다.
Phase 3 테스트는 따옴표·대소문자·인자 검증, 오류 후 입력 계속 받기, 종료 명령과 EOF·Ctrl+C,
실제 프로세스에서의 `main.py` 실행을 확인합니다.
Phase 4 테스트는 저장 순서와 무관한 부모 우선 출력, 여러 부모와 공통 조상, 단절된 이력,
1,500개 커밋의 긴 이력, 없는 커밋·부모와 순환, 조회 전후 상태 보존, 실제 CLI 실행을 확인합니다.
Phase 5 테스트는 양방향·형제·동일 커밋·단절 경로, 거리 우선 선택과 전체 문자열의 사전순 동률 처리,
저장 순서 독립성, 긴 이력, 잘못된 hash·인자, 조회 전후 상태 보존과 실제 CLI 실행을 확인합니다.

## 구현 범위

### 필수 기능

- 저장소 초기화, 사용자 설정, 브랜치 생성과 전환, 커밋 생성
- 부모가 자식보다 먼저 출력되는 기본 로그
- 두 커밋 사이의 최단 경로와 특정 커밋의 모든 조상 탐색
- 키워드와 작성자 역색인을 이용한 검색
- 직접 구현한 정렬을 이용한 날짜순·작성자순 로그
- 따옴표와 오류 처리를 지원하는 반복 입력 CLI
- 주요 함수와 클래스의 주석 또는 docstring, 실행법과 설계 설명

커밋 메타데이터를 다루며 파일 내용 추적, 네트워크 통신, 디스크 저장은 필수 범위에 포함하지 않습니다.
종료하면 메모리의 저장소 데이터는 사라집니다.

### 선택 과제

필수 기능을 완성한 뒤 별도 작업으로 진행합니다.

- 두 텍스트 파일을 줄 단위로 비교하는 `DIFF`
- 두 부모를 갖는 커밋을 만드는 `MERGE`
- 두 가지 이상 정렬 알고리즘의 실행 시간 비교

## 핵심 자료구조

| 데이터 | 역할 | 표현 계획 |
| --- | --- | --- |
| `Commit` | 커밋 하나의 기록 | `hash`, `message`, `author`, `timestamp`, `parents` 필드 |
| `commits` | hash로 커밋 조회 | `dict[str, Commit]` |
| `branches` | 브랜치가 가리키는 커밋 | `dict[str, str 또는 None]` |
| `current_branch` | HEAD가 가리키는 현재 브랜치 | 브랜치 이름 |
| `current_user` | 새 커밋의 작성자 | 사용자 이름 |
| `keyword_index` | 토큰으로 검색 후보 조회 | 토큰 → 커밋 hash 집합 |
| `author_index` | 작성자로 검색 후보 조회 | 작성자 → 커밋 hash 집합 |

HEAD는 현재 브랜치 이름으로 표현하고, `branches[current_branch]`로 현재 커밋을 찾습니다.
브랜치는 커밋을 복사하지 않고 특정 커밋을 가리킵니다.
커밋을 만들면 현재 브랜치만 새 커밋을 가리키도록 이동합니다.

`parents`에는 부모 커밋의 hash를 저장합니다. 첫 커밋은 부모가 없고, 일반 커밋은 부모가 하나입니다.
여러 부모도 표현할 수 있도록 리스트를 사용합니다.
새 커밋이 기존 커밋만 부모로 참조하고 생성 후 부모 관계를 변경하지 않도록 하여 DAG를 유지합니다.
DAG는 방향이 있고, 연결을 따라 돌아서 자기 자신으로 되돌아오는 순환이 없는 그래프입니다.

## 명령별 동작

| 명령 | 해야 하는 일 | 상태 변경 |
| --- | --- | --- |
| `INIT <user_name>` | 저장소와 `main` 브랜치 생성, 현재 사용자와 HEAD 설정 | 초기 상태 생성 |
| `BRANCH <branch_name>` | 현재 커밋을 가리키는 브랜치 생성 | 브랜치 추가, 현재 브랜치는 유지 |
| `SWITCH <branch_name>` | 현재 브랜치 전환 | HEAD 변경 |
| `COMMIT <message>` | 현재 커밋을 부모로 새 커밋 생성, hash 출력 | 커밋 추가, 현재 브랜치 이동, 두 역색인 갱신 |
| `LOG` | 저장소 전체 커밋을 부모 우선 순서로 출력 | 없음 |
| `LOG --sort-by=date` | 전체 커밋을 timestamp 오름차순으로 출력 | 없음 |
| `LOG --sort-by=author` | 전체 커밋을 작성자 이름 오름차순으로 출력 | 없음 |
| `PATH <commit1> <commit2>` | 부모 연결을 양방향으로 보고 최소 간선 수 경로 출력 | 없음 |
| `ANCESTORS <commit_hash>` | 부모 연결을 따라 모든 조상 출력 | 없음 |
| `SEARCH <keyword>` | 키워드 역색인으로 커밋 검색 | 없음 |
| `SEARCH --author=<name>` | 작성자 역색인으로 커밋 검색 | 없음 |
| `exit` / `quit` | 프로그램 종료 | 메모리 데이터 소멸 |

커밋 목록 출력에는 hash, author, timestamp, message를 포함합니다.

## 입력과 동작 규칙

다음은 요구사항을 구현하기 위한 프로젝트 규칙입니다.
요구사항에서 선택을 허용하거나 의미를 확정하지 않은 부분도 여기에 명시합니다.

### 입력과 오류

- 명령어 이름은 대소문자를 구분하지 않습니다. 인자의 원래 내용은 유지합니다.
- 옵션 이름과 값은 명세에 나온 소문자 표기를 사용합니다.
- 공백이 있는 인자는 따옴표로 감쌉니다. 예: `INIT "Alice Kim"`, `COMMIT "Add login feature"`.
- 작성자 옵션도 `SEARCH --author="Alice Kim"`처럼 입력합니다.
- `shlex.split()`으로 따옴표를 처리하고 인자 개수를 검사합니다. 옵션 형식은 해당 기능의 Phase에서 구현합니다.
- 빈 사용자명, 빈 브랜치 이름, 빈 메시지, 빈 검색어는 허용하지 않습니다.
- 잘못된 입력은 오류를 출력하고 다음 입력을 받습니다.
- EOF 입력이나 Ctrl+C로도 정상 종료합니다.

| 상황 | 오류 메시지 |
| --- | --- |
| 초기화 전에 저장소 명령 실행 | `Repository not initialized` |
| 같은 세션에서 다시 초기화 | `Repository already initialized` |
| 인자 개수·옵션·따옴표 오류 또는 빈 인자 | `Invalid args` |
| 지원하지 않는 명령 | `Unknown command: <command>` |
| 같은 이름의 브랜치 생성 | `Branch already exists: <name>` |
| 존재하지 않는 브랜치 사용 | `Unknown branch: <name>` |
| 존재하지 않는 커밋 사용 | `Unknown commit: <hash>` |

### 커밋과 브랜치

- 초기화 직후 `main`이 가리키는 커밋은 `None`입니다.
- 커밋이 없는 상태에서도 브랜치를 생성하거나 전환할 수 있습니다.
- 부모가 될 현재 커밋이 없으면 새 커밋의 `parents`는 빈 리스트입니다.
- hash는 증가 카운터를 기반으로 세션 내 중복 없이 생성합니다. 예: `c000001`.
- timestamp는 커밋 생성 시각을 저장합니다.
- 브랜치 이름과 작성자 이름은 대소문자를 구분합니다.
- 사용자 변경 명령은 필수 범위에 추가하지 않습니다. 여러 작성자 검증은 테스트 데이터로 수행합니다.

### 로그와 탐색

- 기본 `LOG`는 현재 브랜치뿐 아니라 저장소의 모든 커밋을 출력합니다.
- 모든 부모가 자식보다 먼저 나오도록 위상 정렬을 사용합니다. 서로 선후 관계가 없는 커밋의 순서는 자유입니다.
- 정렬 옵션이 있으면 날짜 또는 작성자 기준을 적용합니다. 작성자순 로그는 부모 우선 순서를 보장하지 않습니다.
- 정렬값이 같으면 기본 로그의 상대 순서를 유지하는 안정 정렬을 사용합니다.
- `PATH`는 간선 수가 가장 적은 경로를 선택합니다. 동률이면 `hash1->hash2->...` 문자열의 사전순으로 선택합니다.
- 출발점과 도착점이 같으면 해당 커밋 하나를 출력합니다. 연결이 없으면 `No path`를 출력합니다.
- `ANCESTORS`는 시작 커밋 자신을 제외하고 모든 조상을 중복 없이 출력합니다. 출력 순서는 자유입니다.
- 빈 로그·조상·검색 결과는 결과가 없음을 알리는 메시지를 출력합니다.

### 검색과 정렬

- 메시지는 `split()`으로 공백 분리한 뒤 `lower()`로 정규화해 색인합니다.
- 같은 메시지에 반복된 토큰은 해당 커밋을 한 번만 등록합니다.
- 키워드는 부분 문자열이 아닌 정규화된 토큰과 정확히 일치해야 합니다.
- 구두점은 제거하지 않습니다. `login`과 `login!`은 서로 다른 토큰입니다.
- 공백이 있는 검색어는 같은 방식으로 토큰화하고, 모든 토큰을 포함한 커밋을 찾는 AND 검색으로 해석합니다.
  이는 요구사항에 의미가 명시되지 않은 복수 단어 검색에 대한 프로젝트 결정입니다.
- 작성자는 이름 전체가 일치해야 합니다. 작성자 색인에는 소문자 정규화를 적용하지 않습니다.
- 검색은 색인에서 hash 후보를 가져옵니다. 검색할 때 모든 커밋 메시지를 순회하지 않습니다.
- 그래프 전용 라이브러리와 표준 정렬 API(`sorted()`, `list.sort()` 등)는 사용하지 않습니다.
  경로 탐색의 동률 처리를 위한 정렬에도 이 제한을 적용합니다.
- 날짜와 작성자 정렬에는 비교 기준을 바꿀 수 있는 병합 정렬을 직접 구현합니다.

## 파일 구조 계획

아래 파일은 해당 Phase에서 필요할 때 생성합니다.

```text
main.py          # 실행 진입점, 명령 파싱, 입력과 출력
models.py        # Commit 자료구조
repository.py    # 저장소 상태, 초기화, 커밋과 브랜치 관리
graph.py         # 위상 정렬, 조상 탐색, 최단 경로
search.py        # 역색인 생성·갱신과 검색
sorting.py       # 직접 구현한 정렬
tests/           # 상태 변화, 알고리즘, CLI 검증
README.md        # 실행법, 동작 규칙, 학습 계획
```

알고리즘은 입력·출력 처리와 분리된 함수 또는 클래스로 구현합니다.
각 Phase에서 완료 기준을 확인한 뒤 커밋하고, 다음 Phase로 진행합니다.

## 학습 및 커밋 계획

### Phase 0 — 요구사항 분석과 설계

학습: 필수 요구사항과 설계 결정 구분하기, 작업을 작은 단위로 나누기.

- [x] 필수 기능과 선택 과제 구분
- [x] 실행 계획과 명령별 동작 정리
- [x] 입력·오류·검색·정렬의 해석 결정
- [x] 핵심 자료구조와 파일 역할 정의
- [x] Phase별 학습 내용과 완료 기준 작성

완료 기준: 각 명령이 어떤 상태를 변경하고 무엇을 조회하는지 설명할 수 있다.

커밋: `docs: Mini Git 요구사항 및 단계별 구현 계획 정리`

### Phase 1 — 커밋 모델과 저장소 초기화

학습: 클래스 또는 dataclass, `dict`, `list`, `None`.

- [x] `Commit`의 필수 필드와 여러 부모를 담는 구조 정의
- [x] 저장소 상태와 중복 없는 hash 생성 방식 구현
- [x] 초기화, 초기화 전 접근, 반복 초기화 처리
- [x] 초기 사용자, 빈 `main`, 현재 브랜치 확인

완료 기준: 초기화 결과와 오류 동작을 메서드 호출로 확인할 수 있다.

커밋: `feat: 커밋 모델 및 저장소 초기화 구현`

### Phase 2 — 커밋과 브랜치 관리

학습: 참조, 상태 변경, 부모 관계, DAG.

- [x] 커밋 생성과 현재 브랜치 이동 구현
- [x] 브랜치 생성과 전환 구현
- [x] 중복 이름과 없는 브랜치 오류 처리
- [x] 첫 커밋, 빈 브랜치, 브랜치 분기 후 독립적인 위치 변화 검증

완료 기준: 분기한 한쪽에 커밋해도 다른 브랜치의 위치가 바뀌지 않는다.
역색인 갱신은 Phase 6에서 커밋 생성 흐름에 연결한다.

커밋: `feat: 커밋 생성 및 브랜치 관리 구현`

### Phase 3 — 기본 CLI 연결

학습: REPL, 문자열 파싱, 입력 처리와 저장소 로직의 분리.

- [x] 프롬프트 반복과 기본 명령 연결
- [x] 명령어 대소문자, 따옴표, 인자 검증 처리
- [x] 오류 후 반복 입력과 `exit`·`quit`·EOF 종료 처리

완료 기준: `python main.py`에서 초기화·커밋·브랜치 명령을 실행할 수 있다.

커밋: `feat: 기본 명령 파싱 및 CLI 구현`

### Phase 4 — 기본 로그와 조상 탐색

학습: 방향 그래프, Kahn 위상 정렬, DFS 또는 BFS, 방문 집합.

- [x] 부모 목록으로 부모 수와 자식 조회 구조 구성
- [x] 부모 우선 `LOG`와 중복 없는 `ANCESTORS` 구현 및 CLI 연결
- [x] 분기한 이력과 여러 부모가 있는 테스트 그래프 검증

완료 기준: 모든 부모가 자식보다 먼저 출력되고, 공통 조상도 한 번만 출력된다.

커밋: `feat: 위상 정렬 로그 및 조상 탐색 구현`

### Phase 5 — 최단 경로 탐색

학습: 무방향 인접 목록, BFS, 경로 복원, 최단 경로 동률 처리.

- [x] 부모 연결을 양방향으로 조회하는 구조 구성
- [x] BFS 거리와 다음 이동 위치를 이용한 경로 복원 구현
- [x] 여러 최단 경로 중 전체 경로 문자열의 사전순 선택 보장
- [x] `PATH` 연결 및 같은 커밋·없는 커밋·단절·동률 경로 검증
- [x] 전체 경로 문자열 비교로 동률 처리하여 이웃 정렬 없이 구현

완료 기준: 형제 커밋 사이도 탐색하고, 여러 최단 경로 예제에서 지정된 경로를 선택한다.
단절과 여러 경로는 테스트용 그래프로 구성한다.

커밋: `feat: BFS 기반 커밋 최단 경로 탐색 구현`

### Phase 6 — 역색인 검색

학습: 역색인, 집합, 교집합, 검색 비용.

- [ ] 키워드·작성자 색인과 커밋 생성 시 갱신 구현
- [ ] 단일 키워드, 여러 토큰 AND 검색, 작성자 검색 연결
- [ ] 대소문자 정규화, 반복 토큰, 구두점, 빈 결과 검증

완료 기준: 전체 메시지 순회 없이 검색하고 결과 커밋이 중복되지 않는다.

커밋: `feat: 키워드 및 작성자 역색인 검색 구현`

### Phase 7 — 정렬 알고리즘과 로그 옵션

학습: 병합 정렬, 비교 기준, 안정 정렬, 시간·공간 복잡도.

- [ ] 비교 기준을 바꿀 수 있는 병합 정렬 구현
- [ ] 날짜순·작성자순 로그 연결과 동률 순서 검증
- [ ] 출력 정렬이 저장소 관계를 변경하지 않는지 확인
- [ ] 표준 정렬 API 사용 여부 점검

완료 기준: 두 정렬 기준과 안정성이 검증되고, 평균·최악 시간복잡도를 설명할 수 있다.

커밋: `feat: 병합 정렬 및 로그 정렬 옵션 구현`

### Phase 8 — 통합 검증과 제출 정리

학습: 통합 시나리오, 경계 조건, 문서화.

- [ ] 초기화부터 분기·탐색·검색·정렬까지 전체 흐름 검증
- [ ] 빈 저장소와 잘못된 입력 이후에도 CLI가 작동하는지 확인
- [ ] 여러 작성자를 가진 테스트 데이터로 검색과 정렬 확인
- [ ] 주요 함수와 클래스의 주석 또는 docstring 정리
- [ ] 실제 실행 예시, 테스트 실행법, 알고리즘 복잡도를 README에 반영

완료 기준: README를 따라 실행할 수 있고 필수 명령의 정상·오류 사례가 검증된다.

커밋: `test: 전체 명령 흐름 검증 및 사용 문서 보완`

## Phase 0 설계 확인 예제

다음은 구현 후 확인할 시나리오입니다.

```text
INIT Alice
COMMIT "Initial commit"
BRANCH feature
SWITCH feature
COMMIT "Add login"
SWITCH main
COMMIT "Add payment"
```

기대하는 상태는 다음과 같습니다. hash는 설명을 위한 예시입니다.

```text
c000001 Initial commit
├── c000002 Add login      ← feature
└── c000003 Add payment    ← main, 현재 브랜치
```

- `BRANCH feature`는 브랜치만 추가하고 커밋은 생성하지 않습니다.
- `SWITCH`는 현재 브랜치만 바꾸고 커밋은 생성하지 않습니다.
- `c000002`, `c000003`의 부모는 모두 `c000001`입니다.
- 기본 `LOG`에서 `c000001`은 나머지 두 커밋보다 먼저 나옵니다.
- `PATH c000002 c000003`은 `c000002 -> c000001 -> c000003`입니다.
- `ANCESTORS c000003`의 결과는 `c000001`입니다.
- `SEARCH login`의 결과는 `c000002`입니다.
