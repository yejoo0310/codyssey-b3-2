# Mini Git

Git의 커밋 그래프와 브랜치 관리를 메모리에서 구현한 CLI 프로그램입니다.
커밋 메타데이터를 저장하고, 로그 조회·최단 경로·조상 탐색·역색인 검색·정렬을 지원합니다.

## 실행 환경

- Python 3.10 이상
- 외부 패키지 설치 불필요

프로젝트 디렉터리에서 실행합니다.

```bash
python main.py
```

환경에 따라 `python3 main.py`로 실행할 수 있습니다.
`mini-git>` 프롬프트에 명령을 입력하며, `exit` 또는 `quit`로 종료합니다.
입력 중 EOF 또는 Ctrl+C로도 종료할 수 있습니다.

## 명령어

| 명령 | 동작 |
| --- | --- |
| `INIT <user_name>` | 현재 사용자를 설정하고 빈 `main` 브랜치와 HEAD를 초기화 |
| `BRANCH <branch_name>` | 현재 커밋을 가리키는 새 브랜치 생성 |
| `SWITCH <branch_name>` | 현재 브랜치 전환 |
| `COMMIT <message>` | 현재 커밋을 부모로 새 커밋 생성, 현재 브랜치와 역색인 갱신 |
| `LOG` | 저장소 전체 커밋을 부모가 자식보다 먼저 나오도록 출력 |
| `LOG --sort-by=date` | 전체 커밋을 생성 시각 오름차순으로 출력 |
| `LOG --sort-by=author` | 전체 커밋을 작성자 이름 오름차순으로 출력 |
| `PATH <commit1> <commit2>` | 부모 연결을 양방향으로 보고 최소 간선 수 경로 출력 |
| `ANCESTORS <commit_hash>` | 해당 커밋의 모든 조상을 중복 없이 출력 |
| `SEARCH <keyword>` | 역색인으로 키워드가 일치하는 커밋 검색 |
| `SEARCH --author=<name>` | 작성자 이름 전체가 일치하는 커밋 검색 |
| `exit` / `quit` | 프로그램 종료 |

명령어 이름은 대소문자를 구분하지 않습니다. 인자의 대소문자는 유지합니다.
공백이 있는 인자는 따옴표로 감쌉니다.
옵션 이름과 값은 위 표의 소문자 형식을 사용합니다.

```text
INIT "Alice Kim"
COMMIT "Add login feature"
SEARCH "login feature"
SEARCH --author="Alice Kim"
```

## 사용 예시

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
mini-git> COMMIT "Add login feature"
[feature c000002] Add login feature
mini-git> SWITCH main
Switched to branch: main
mini-git> COMMIT "Add payment feature"
[main c000003] Add payment feature
mini-git> PATH c000002 c000003
Path: c000002 -> c000001 -> c000003
mini-git> quit
```

위 예제의 커밋 관계와 브랜치 위치는 다음과 같습니다.

```text
c000001 Initial commit
├── c000002 Add login feature      ← feature
└── c000003 Add payment feature    ← main
```

모든 필수 명령을 순서대로 실행하는 예제도 제공합니다.

```bash
python3 main.py < examples/session.txt
```

## 동작 규칙

### 커밋과 브랜치

- 커밋은 `hash`, `message`, `author`, `timestamp`, `parents`를 가집니다.
- `commits` 딕셔너리에서 hash로 커밋을 조회하고, 브랜치는 커밋 hash 또는 `None`을 가리킵니다.
- HEAD는 현재 브랜치 이름으로 표현합니다. 브랜치 생성만으로 현재 브랜치가 바뀌지는 않습니다.
- 초기화 직후 커밋은 없습니다. 빈 브랜치에서 만든 첫 커밋은 부모가 없습니다.
- 새 커밋은 기존 커밋만 부모로 참조하며, 커밋 생성 과정에서 과거 부모 관계를 바꾸지 않아 DAG를 유지합니다.
- 부모는 여러 개를 담을 수 있지만, 기본 `COMMIT`은 현재 커밋 하나를 부모로 사용합니다.
- hash는 증가 카운터로 생성하여 저장소 세션 내 중복을 방지합니다. 예: `c000001`.
- 시각은 한국 시간(KST)으로 저장하고 `YYYY-MM-DD HH:MM:SS` 형식으로 출력합니다. 시간대 숫자는 화면에 표시하지 않습니다.
- 사용자 변경 명령은 제공하지 않습니다.
- 커밋에는 생성 당시 브랜치 이름도 저장합니다.

### 로그와 탐색

- `LOG`는 현재 브랜치에 한정하지 않고 전체 커밋을 위상 정렬합니다. 선후 관계가 없는 커밋의 상대 순서는 자유입니다.
- 기본·정렬 로그는 커밋 헤더 끝에 생성 당시 브랜치를 `[main]`, `[feature]`처럼 표시합니다. 브랜치의 현재 위치와는 구분됩니다.
- 정렬 옵션은 지정한 기준을 우선합니다. 동률이면 기본 로그의 상대 순서를 유지하는 안정 정렬을 적용합니다.
- 작성자 이름은 대소문자를 구분하는 Python 문자열 비교 순서로 정렬합니다.
- 정렬 옵션이 있는 로그는 부모 우선 순서를 별도로 보장하지 않습니다.
- `PATH`의 최단 경로가 여러 개면 공백 없는 `hash1->hash2->...` 문자열이 사전순으로 가장 작은 경로를 선택합니다.
- 경로가 없으면 `No path`, 출발점과 도착점이 같으면 해당 커밋 하나를 출력합니다.
- `ANCESTORS`는 시작 커밋 자신을 제외하고 부모 방향으로 탐색합니다. 출력 순서는 자유입니다.
- 로그·조상·검색 결과는 hash, 작성자, 시각, 메시지를 포함하며, 빈 결과는 `No commits found.`를 출력합니다.

### 검색

- 메시지를 공백 기준으로 분리하고 소문자로 정규화한 토큰을 색인에 저장합니다.
- 키워드는 토큰 단위로 정확히 일치해야 합니다. `log`는 `login`과 일치하지 않습니다.
- 구두점을 제거하지 않으므로 `login`과 `login!`은 다른 토큰입니다.
- 여러 단어 검색은 모든 토큰을 포함하는 AND 검색입니다. 단어의 순서와 인접 여부는 검사하지 않습니다.
- 작성자는 공백과 대소문자를 포함한 이름 전체가 정확히 일치해야 합니다.
- 검색 범위는 전체 저장소이며 결과 순서는 자유입니다. 검색할 때 모든 메시지를 순회하지 않습니다.
- `--`로 시작하는 검색 인자는 옵션으로 해석하며, `--author=<name>`만 지원합니다.

## 오류 처리

잘못된 입력은 오류를 출력한 뒤 같은 저장소 상태로 다음 명령을 받습니다.
빈 입력은 무시하며, 공백뿐인 인자는 허용하지 않습니다.

| 상황 | 메시지 |
| --- | --- |
| 초기화 전 저장소 명령 | `Repository not initialized` |
| 반복 초기화 | `Repository already initialized` |
| 잘못된 인자·옵션·따옴표 | `Invalid args` |
| 알 수 없는 명령 | `Unknown command: <COMMAND>` |
| 중복 브랜치 | `Branch already exists: <name>` |
| 없는 브랜치 | `Unknown branch: <name>` |
| 없는 커밋 | `Unknown commit: <hash>` |

## 구조와 알고리즘

```text
main.py          # 실행 진입점, 명령 파싱, REPL과 출력
models.py        # Commit 자료구조
repository.py    # 저장소 상태와 명령별 동작
graph.py         # 위상 정렬, 조상 탐색, 최단 경로
search.py        # 키워드·작성자 역색인
sorting.py       # 직접 구현한 안정 병합 정렬
examples/        # CLI 입력 예제
tests/           # 단위 테스트와 통합 테스트
```

알고리즘은 입력·출력 처리와 분리했습니다. 그래프 전용 라이브러리와 `sorted()`, `list.sort()` 같은 표준 정렬 API는 사용하지 않습니다.

`V`는 전체 커밋 수, `E`는 부모 연결 수, `Va`·`Ea`는 조상 탐색의 방문 범위,
`K`는 검색 결과 수, `L`은 PATH에서 저장하는 경로 문자열의 최대 길이입니다.

| 기능 | 구현 | 시간복잡도 | 추가 공간 |
| --- | --- | --- | --- |
| 기본 로그 | Kahn 위상 정렬 | `O(V + E)` | `O(V + E)` |
| 조상 탐색 | 스택 기반 부모 탐색 | `O(Va + Ea)` | `O(Va)` |
| 최단 경로 | 도착점 BFS + 거리순 경로 문자열 비교 | 최악 `O((V + E) × L)` | `O(V + E + V × L)` |
| 단일 키워드·작성자 검색 | 해시맵 역색인 | 평균 `O(1 + K)`, 검색어 처리 별도 | 후보·결과 `O(K)`, 색인 공간 별도 |
| 정렬 옵션 로그 | 위상 정렬 + 병합 정렬 | `O(V + E + V log V)` | `O(V + E)` |

`merge_sort(commits, key="date")` 또는 `merge_sort(commits, key="author")`처럼 문자열로 정렬 기준을 지정합니다.
딕셔너리·집합 조회와 정렬값 비교를 평균 일정 비용으로 보는 기준입니다.
여러 토큰 검색에는 후보 집합의 복사·교집합 비용이 추가됩니다.
병합 정렬은 평균·최악 `O(n log n)`, 추가 공간 `O(n)`이며, 동률일 때 왼쪽 원소를 먼저 선택해 안정성을 유지합니다.
경로 문자열과 작성자 문자열의 길이, 출력량도 실제 비용에 영향을 줍니다.

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

Python 3.10.10에서 108개 테스트를 검증했습니다.
커밋·브랜치 상태 변화, 여러 부모를 가진 DAG, 깊은 이력, 경로 동률,
전체 메시지 순회 없는 검색, 정렬 안정성, 입력 오류와 종료, 실제 CLI 프로세스의 전체 흐름을 확인합니다.

통합 테스트만 실행하려면 다음 명령을 사용합니다.

```bash
python3 -m unittest discover -s tests -p test_workflows.py -v
```

## 구현 범위

커밋 메타데이터를 다루는 메모리 기반 프로그램입니다. 파일 내용 추적과 네트워크 통신은 구현하지 않습니다.
저장소를 파일로 저장하지 않으므로 종료 후 재실행하면 초기화 전 상태에서 시작합니다.
선택 과제인 `DIFF`, `MERGE` 명령과 정렬 알고리즘 성능 비교는 구현 범위에 포함하지 않았습니다.
