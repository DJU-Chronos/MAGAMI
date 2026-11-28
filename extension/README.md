# 마감이 크롬 확장 프로그램

지금 열려 있는 공지에서 버튼 한 번으로 신청 기간·마감일을 정리하고, 구글 캘린더에 추가합니다.

## 설치 (5분)

1. 이 레포를 내려받습니다. (GitHub 초록색 **Code** → **Download ZIP** → 압축 풀기, 또는 `git clone`)
2. 크롬 주소창에 `chrome://extensions` 를 엽니다.
3. 오른쪽 위 **개발자 모드**를 켭니다.
4. **압축해제된 확장 프로그램을 로드합니다**를 누르고 레포 안의 **`extension` 폴더**를 고릅니다.
5. 퍼즐 모양 아이콘에서 **마감이**를 고정(핀)합니다.

## API 키 넣기

1. [Google AI Studio](https://aistudio.google.com/)에 로그인 → **Get API key** → 키 만들기
2. 마감이 아이콘 → **설정** → 키를 붙여넣고 **저장**

키는 이 브라우저에만 저장됩니다. 다른 사람과 공유하거나 레포에 올리지 마세요.

## 사용하기

1. 학교·사업단 홈페이지 등에서 **공지 글을 직접 엽니다.**
2. 마감이 아이콘 → **이 공지 정리하기**
   - **포스터 이미지도 함께 보내기**(기본 켜짐): 페이지에 이미 떠 있는 큰 이미지(최대 3장)를 같이 보냅니다. 읽을 수 없는 이미지뿐이면 지금 보이는 화면을 대신 보냅니다.
3. 결과를 **원문과 대조**하고, 틀린 칸(행사명·마감일·시각·신청 기간·대상·신청 방법)은 **직접 고칩니다.**
4. **확인하고 저장** → 확장의 **내 마감 목록**에 D-day와 함께 저장됩니다 (이 브라우저에만 저장)
5. **구글 캘린더에 추가** → 열린 구글 캘린더 화면에서 **저장** (고친 값이 들어갑니다)
6. (선택) **JSON** 또는 내 마감 목록의 **전체 JSON 저장** → 공지 체크 화면(Streamlit)에 올릴 수 있습니다.

## 지키는 원칙

- 버튼을 **누를 때만**, **지금 탭 하나만** 읽습니다 (`activeTab` 권한). 모든 사이트에 자동으로 붙지 않습니다.
- 공지 목록을 돌거나 다른 페이지를 열지 않습니다. 포스터도 **이미 화면에 불러온 이미지**를 쓰고 새로 내려받지 않습니다.
- 본문은 [Mozilla Readability](https://github.com/mozilla/readability)(Apache-2.0)로 찾고, 실제 페이지는 건드리지 않도록 복사본에서 실행합니다.
- 읽은 본문은 Gemini 정리에만 쓰고 저장하지 않습니다. 저장·내보내기는 정리된 항목과 원문 링크뿐입니다.
- 학교 이용 기준에서 이 방식이 허용되는지는 별도 확인이 필요합니다. 자세한 내용은 [`docs/collection-policy.md`](../docs/collection-policy.md).

## 개발자용

| 파일 | 역할 |
|---|---|
| `manifest.json` | 권한: `activeTab`, `scripting`, `storage` + Gemini 주소 |
| `popup.html` · `popup.js` · `popup.css` | 버튼, 탭 읽기, Gemini 호출, 결과 카드 |
| `lib.js` | 날짜 정리·id·캘린더 링크·수정값 반영·내 마감 목록 정렬 (파이썬 `src/magami/extract.py`와 같은 규칙) |
| `vendor/Readability.js` | Mozilla Readability 0.6.0 (Apache-2.0, 원본 그대로, `vendor/Readability.LICENSE.md`) |
| `options.html` · `options.js` | API 키·모델 설정 |
| `prompt.md` | 공통 프롬프트 사본 — **직접 고치지 말고** `prompts/extract_notice.md`를 고친 뒤 `python scripts/sync_prompt.py` |
