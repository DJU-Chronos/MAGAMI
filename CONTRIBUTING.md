# 협업 규칙

## 작업 흐름

1. **Issue 만들기** — 모든 작업은 Issue로 등록하고 담당자(Assignees)를 지정한다.
2. **브랜치 만들기** — `main`에서 작업 브랜치를 만든다.
3. **커밋** — 아래 규칙에 맞춰 커밋한다.
4. **Pull Request** — `main`으로 PR을 열고 템플릿을 채운다.
5. **리뷰** — 다른 팀원 **1명 이상 승인(Approve)** 후 머지한다. (`main`은 보호되어 직접 push할 수 없다.)

## 명령어로 하는 작업 순서

Claude Code에 시켜도 되지만, 무엇이 일어나는지 알고 있으면 막혔을 때 빨리 풀 수 있다.

```bash
# 1. 시작 전: main을 최신으로
git switch main
git pull origin main

# 2. 작업 브랜치 만들기 (Issue 하나당 하나)
git switch -c feat/homepage-collector

# 3. 기능 하나씩: 구현 → 실행·테스트 → 커밋 (작게 여러 번)
python -m unittest discover -s tests
git status
git add src/magami/collect_homepage.py tests/test_collect_homepage.py
git commit -m "[기능] 메인 공지 칸 파싱 추가 (#12)"

# 4. 처음 올릴 때만 -u (이후엔 git push)
git push -u origin feat/homepage-collector
```

5. GitHub에서 PR 만들기 → 리뷰어 지정 → 승인 → **Create a merge commit**으로 머지
6. 머지 후 내 컴퓨터 맞추기

```bash
git switch main
git pull origin main
git status                      # "nothing to commit, working tree clean"이면 정상
python -m unittest discover -s tests
```

### 기록 확인

```bash
git log --oneline --graph --all --decorate   # 브랜치·머지 흐름 한눈에 보기
git log --author="<내 GitHub 아이디>" --oneline  # 내 커밋만 보기
```

### 자주 생기는 상황

| 상황 | 해결 |
|---|---|
| push가 거절됨 (`rejected ... fetch first`) | `git pull origin <내 브랜치>` 후 다시 push |
| PR에 "This branch has conflicts" | Claude Code에 "PR #번호 충돌을 main 기준으로 해결해 줘" → 해결 커밋 push → **다시 승인 필요** |
| 비밀 파일을 이미 커밋함 | `.gitignore`에 추가해도 이미 올라간 파일은 빠지지 않는다. 바로 팀장에게 알리고 키를 폐기·재발급 |
| main에 직접 push가 안 됨 | 정상이다. main은 보호되어 PR로만 바뀐다 |

## 브랜치 이름

영문 소문자, 숫자, 하이픈(-), 슬래시(/)만 쓴다. 한글과 공백은 쓰지 않는다.

| 접두어 | 용도 | 예시 |
|---|---|---|
| `feat/` | 기능 추가 | `feat/homepage-collector` |
| `fix/` | 오류 수정 | `fix/deadline-parsing` |
| `docs/` | 문서 | `docs/channel-list` |
| `chore/` | 설정·환경 | `chore/initial-structure` |

## 커밋 메시지

```
[말머리] 무엇을 했는지 한 줄 요약 (#Issue번호)
```

| 말머리 | 의미 |
|---|---|
| `[기능]` | 기능 추가·변경 |
| `[수정]` | 오류 수정 |
| `[문서]` | 문서 작성·수정 |
| `[설정]` | 환경·설정·폴더 구조 |
| `[테스트]` | 테스트·평가 |

예시: `[기능] 메인 공지 칸 수집기 추가 (#12)`

## Pull Request

- 변경 내용, 확인 방법, **AI 사용 여부**를 반드시 적는다.
- 본문에 `Closes #번호`를 쓰면 머지할 때 Issue가 자동으로 닫힌다.
- 리뷰어는 직접 실행하거나 변경 내용을 읽고 확인한 뒤 승인한다.

## AI 도구 사용 규칙

### AI로 작업할 때 순서

1. **분석·설계 먼저**: 코드를 바로 만들게 하지 말고, Issue 내용을 주고 "아직 코드를 쓰지 말고 무엇을 어떤 순서로 만들지 먼저 정리해 줘"라고 요청한다. 정리된 계획을 읽고 고친다.
2. **기능 하나씩**: 전체를 한 번에 만들게 하지 않는다. 기능 하나 → 실행·테스트로 확인 → 커밋을 반복한다.
3. **결과는 직접 확인**: AI가 "됐다"고 해도 직접 실행해 본 결과만 PR의 "확인 방법"에 적는다.
4. **문서와 실제를 맞춘다**: 기능을 바꾸면 README·안내서도 같은 PR에서 고친다.

### 규칙

- AI(Claude Code, Gemini 등)로 만든 코드·문서는 **작성자가 직접 실행·검토한 뒤** PR로 올린다.
- PR 템플릿의 "AI 사용 여부"에 사용한 도구와 범위를 적는다.

## 비밀 정보

- API 키, 토큰, 비밀번호는 절대 커밋하지 않는다. 로컬은 `.env`, 자동 실행은 GitHub Secrets에 저장한다.
- `.env.example`에는 **변수 이름만** 적는다.
- 실수로 올렸다면 즉시 팀장에게 알리고 해당 키를 폐기·재발급한다. (삭제 커밋만으로는 기록에 남는다.)

## 회의

- 주 1회 대면 회의, 회의록은 [GitHub Wiki](../../wiki)에 기록한다.
- 주간 요약은 [`docs/weekly-log.md`](docs/weekly-log.md)에 남긴다.
