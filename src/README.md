# src

소스코드를 보관합니다.

- 수집기: 홈페이지 메인 공지 칸 (제목·날짜·링크)
- AI 정리: Gemini API로 공지 판별·정보 추출
- 공지 체크 화면: Streamlit
- 캘린더 등록, 알림

## 지금 있는 모듈

| 파일 | 하는 일 |
|---|---|
| `magami/daily.py` | 하루 1회 실행: 메인 공지 칸 수집 → 저장 → 새 공지 알림 ([`docs/daily-automation.md`](../docs/daily-automation.md)) |
| `magami/collect_homepage.py` | 허용된 메인 페이지의 공지 칸에서 제목·게시일·링크 수집 (robots.txt 확인, 아래 설명) |
| `magami/store.py` | `notices.json` 읽기·쓰기, 새 공지 골라내기 (사용자가 정리한 마감일은 덮어쓰지 않음) |
| `magami/notify.py` | 새 공지 이메일 알림 (Gmail 앱 비밀번호) |
| `magami/extract.py` | 공지 본문(+포스터)을 Gemini로 정리해 [`docs/schema.md`](../docs/schema.md) 형식 JSON으로 만든다. 프롬프트는 [`prompts/extract_notice.md`](../prompts/extract_notice.md)를 쓴다 |

```bash
pip install -r requirements.txt
pip install -e .
python -m magami.extract --text-file data/raw/공지.txt --url https://... --posted-at 2026-11-20
```

`.env`에 `GEMINI_API_KEY`가 있어야 한다. 모델은 `GEMINI_MODEL`로 바꿀 수 있다 (기본 `gemini-2.5-flash`).

### 메인 공지 칸 수집기 (`magami/collect_homepage.py`)

[`config/channels.yaml`](../config/channels.yaml)에서 `enabled`·`robots_allowed`가 `true`인 사이트의 메인 페이지만 하루 1번 요청해, 공지 칸의 **제목·게시일·원문 링크**만 가져온다. 결과는 `source: auto`이고 마감일 등은 비어 있다.

- 요청 전에 `robots.txt`를 확인한다 (`*`, `$` 규칙 지원). 허용되지 않으면 요청하지 않는다.
- 공지 목록·본문 페이지(`/*/na/ntt/`)는 열지 않는다. 글 주소만 저장한다.
- 공지 칸 제목이 '공지사항'이 아닌 사이트는 `channels.yaml`에 `tab`으로 적는다 (예: 대학혁신지원사업 `사업단소식`).

```bash
python -m magami.collect_homepage          # 채널별 공지 목록 보기
python -m magami.collect_homepage --json   # schema 형식 JSON으로 보기
```

매일 자동 실행(`magami/daily.py`)은 이 파일의 `collect(channel)`을 부른다.
