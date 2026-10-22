# 공지 데이터 형식과 정확도 기준

AI 정리 결과와 정답 자료(`data/ground_truth/`)는 **같은 형식**을 사용한다. 그래야 정확도를 자동으로 계산할 수 있다.

## 공지 1건의 형식

```json
{
  "id": "instagram_daejeon_univ_3412345",
  "source": "instagram",
  "channel": "@daejeon_univ",
  "url": "https://www.instagram.com/p/XXXX/",
  "posted_at": "2026-10-13",
  "is_notice": true,
  "title": "2026 AI·OSS 프로젝트 동아리 모집",
  "apply_start": "2026-09-30",
  "apply_end": "2026-10-11",
  "deadline": "2026-10-11",
  "deadline_time": null,
  "target": "SW융합대학 재학생",
  "how_to_apply": "신청서 작성 후 이메일 제출",
  "collected_at": "2026-10-14T09:00:00+09:00"
}
```

| 필드 | 설명 | 값 규칙 |
|---|---|---|
| `id` | 공지 고유 번호 | `출처_채널_게시물번호` |
| `source` | 출처 종류 | `instagram` 또는 `homepage` |
| `channel` | 채널 이름 | 인스타그램은 `@계정`, 홈페이지는 사이트 이름 |
| `url` | 원문 링크 | 항상 포함 |
| `posted_at` | 게시일 | `YYYY-MM-DD` |
| `is_notice` | 신청 기간·마감일이 있는 공지인지 | `true` / `false` (홍보 영상 등은 `false`) |
| `title` | 행사명 | 문자열 |
| `apply_start` | 신청 시작일 | `YYYY-MM-DD`, 없으면 `null` |
| `apply_end` | 신청 종료일 | `YYYY-MM-DD`, 없으면 `null` |
| `deadline` | 마감일 (캘린더에 등록할 날짜) | `YYYY-MM-DD`, 없으면 `null` |
| `deadline_time` | 마감 시각 | `HH:MM`, 없으면 `null` |
| `target` | 대상 | 문자열 |
| `how_to_apply` | 신청 방법 | 문자열 (개인 연락처는 넣지 않음) |
| `collected_at` | 수집 시각 | ISO 8601, 한국 시간(+09:00) |

- 날짜는 모두 한국 시간 기준이다.
- 게시물에 연도가 없으면 게시일 기준으로 가장 가까운 미래 날짜로 해석한다.

## 정확도 기준

- **주 지표: 마감일 정확도** = `deadline`이 정답과 완전히 일치한 건수 / 30
  - 목표: **90% 이상** (30건 중 27건 이상)
  - 정답이 `null`인 공지에서 AI도 `null`을 내면 일치로 본다.
- **보조 지표**: 공지 판별(`is_notice`) 정확도, 신청 시작일 정확도

## 평가 자료 분리

- **평가용 30건**(`data/ground_truth/eval/`)은 프롬프트를 고치는 데 쓰지 않는다. 쓰면 정확도가 실제보다 높게 나온다.
- 프롬프트 개선에는 **별도의 튜닝용 공지**(`data/ground_truth/tuning/`)를 쓴다.
