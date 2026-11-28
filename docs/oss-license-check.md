# OSS 라이선스 점검표

> 새 오픈소스를 추가할 때는 팀 회의에서 필요성과 라이선스를 확인한 뒤 이 표에 기록합니다.
> 버전은 2단계 개발 시작 시 `requirements.txt`와 함께 확정합니다.

| OSS명 | 버전 | 출처 | 라이선스 | 사용 목적 | 공개 가능 여부 |
|---|---|---|---|---|---|
| Requests |  | https://github.com/psf/requests | Apache-2.0 | 홈페이지 메인 페이지 요청 | 가능 |
| Beautiful Soup |  | https://www.crummy.com/software/BeautifulSoup/ | MIT | 홈페이지 메인 페이지에서 공지 제목·날짜·링크 추출 | 가능 |
| Streamlit |  | https://github.com/streamlit/streamlit | Apache-2.0 | 공지 체크 화면 | 가능 |
| Google API Python Client |  | https://github.com/googleapis/google-api-python-client | Apache-2.0 | 구글 캘린더 등록 | 가능 |
| google-auth-oauthlib |  | https://github.com/googleapis/google-auth-library-python-oauthlib | Apache-2.0 | 구글 계정 로그인 | 가능 |
| Google Gen AI SDK (google-genai) |  | https://github.com/googleapis/python-genai | Apache-2.0 | Gemini API 호출 | 가능 |
| python-dotenv |  | https://github.com/theskumar/python-dotenv | BSD-3-Clause | `.env`에서 API 키 읽기 | 가능 |
| PyYAML |  | https://github.com/yaml/pyyaml | MIT | 채널 목록 파일 읽기 | 가능 |

## 외부 서비스 이용 조건

| 서비스 | 확인할 조건 | 확인일 | 결과 |
|---|---|---|---|
| Gemini API | Gemini API 이용약관, 무료 사용량 |  |  |
| Google Calendar API | Google API 서비스 이용약관 |  |  |
| Chrome 확장 프로그램 | Chrome 웹 스토어 개발자 정책, `activeTab` 권한 범위 |  |  |

## 공개 제한 검토

- 개인정보 포함 여부: 게시물 속 연락처 등 개인정보는 저장하지 않음
- 데이터 공개 제한 여부: 원문 전체를 저장하지 않고 정리한 정보와 원문 링크만 보관
- 비밀 정보: API 키·토큰은 GitHub Secrets에만 보관 (크롬 확장은 사용자 브라우저에만 저장)

> 인스타그램 공식 API는 이번 활동 기간에 쓰지 않는다. ([`decisions.md`](decisions.md) D3)
