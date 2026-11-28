# src

소스코드를 보관합니다.

- 수집기: 홈페이지 메인 공지 칸 (제목·날짜·링크)
- AI 정리: Gemini API로 공지 판별·정보 추출
- 공지 체크 화면: Streamlit
- 캘린더 등록, 알림

## 지금 있는 모듈

| 파일 | 하는 일 |
|---|---|
| `magami/extract.py` | 공지 본문(+포스터)을 Gemini로 정리해 [`docs/schema.md`](../docs/schema.md) 형식 JSON으로 만든다. 프롬프트는 [`prompts/extract_notice.md`](../prompts/extract_notice.md)를 쓴다 |

```bash
pip install -r requirements.txt
pip install -e .
python -m magami.extract --text-file data/raw/공지.txt --url https://... --posted-at 2026-11-20
```

`.env`에 `GEMINI_API_KEY`가 있어야 한다. 모델은 `GEMINI_MODEL`로 바꿀 수 있다 (기본 `gemini-2.5-flash`).
