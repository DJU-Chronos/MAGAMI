# 매일 자동 실행과 새 공지 이메일 알림

[`.github/workflows/daily.yml`](../.github/workflows/daily.yml)이 매일 09:00(한국 시간)에 한 번 실행됩니다.

```
config/channels.yaml의 허용된 메인 공지 칸 → 제목·날짜·링크 수집 (src/magami/collect_homepage.py)
→ data 브랜치의 notices.json과 비교 (src/magami/store.py)
→ 새 공지가 있으면 이메일 알림 (src/magami/notify.py)
→ data 브랜치에 notices.json 저장
```

- 결과를 `main`이 아니라 **`data` 브랜치**에 저장하는 이유: `main`은 보호 규칙(PR + 승인 필수) 때문에 자동 커밋을 받지 않습니다.
- 메인 공지 칸에는 제목·날짜·링크만 있으므로 자동 수집된 공지의 마감일은 비어 있습니다. 메일의 링크를 열고 크롬 확장으로 마감일을 정리합니다.
- 한 채널에서 오류가 나도 나머지 채널은 계속 수집합니다. 모든 채널이 실패했을 때만 실행이 실패(빨간 표시)로 끝납니다.

## 켜는 방법 (fork한 사람도 같음)

### 1. Gmail 앱 비밀번호 만들기

일반 Gmail 비밀번호로는 보낼 수 없습니다. **앱 비밀번호**(16자리)가 필요합니다.

1. 보내는 데 쓸 Google 계정에 **2단계 인증**을 켭니다. (Google 계정 → 보안)
2. Google 계정 → 보안 → **앱 비밀번호** (검색창에 "앱 비밀번호" 입력) → 이름에 `magami` → 만들기
3. 나온 16자리를 복사합니다. 이 화면을 닫으면 다시 볼 수 없습니다.

> 개인 메인 계정 대신 알림 전용 Gmail 계정을 하나 만들어 쓰는 것을 권장합니다.

### 2. GitHub Secrets 등록

레포 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| 이름 | 값 |
|---|---|
| `SMTP_USER` | 보내는 Gmail 주소 |
| `SMTP_PASSWORD` | 앱 비밀번호 16자리 |
| `ALERT_EMAIL_TO` | 받을 주소 (여러 개면 쉼표로 구분) |

Secrets가 없으면 알림만 건너뛰고 수집·저장은 그대로 합니다.

### 3. Actions 권한 확인

레포 → **Settings** → **Actions** → **General** → **Workflow permissions** → **Read and write permissions** → Save

### 4. 실행해 보기

레포 → **Actions** → **매일 공지 수집** → **Run workflow**. 끝나면 `data` 브랜치에 `notices.json`이 생깁니다.

> **fork한 레포**는 예약 실행이 처음에 꺼져 있습니다. Actions 탭에서 "I understand my workflows, go ahead and enable them"을 누르고 위 4번을 한 번 실행하세요. 또 GitHub는 60일 동안 레포에 활동이 없으면 예약 실행을 멈춥니다.

## 내 컴퓨터에서 실행

```bash
pip install -r requirements.txt
pip install -e .
python -m magami.daily --dry-run          # 저장·알림 없이 새 공지만 출력
python -m magami.daily                    # data/notices.json 저장 + (설정돼 있으면) 메일 발송
```

이메일 설정은 `.env`에 같은 이름(`SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO`)으로 넣습니다.
