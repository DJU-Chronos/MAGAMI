"""체크한 공지를 사용자 본인의 구글 캘린더에 일정으로 등록한다.

로그인은 사용자 컴퓨터에서 직접 한다 (OAuth 데스크톱 앱).
- credentials.json: 구글 클라우드 콘솔에서 받은 OAuth 클라이언트 파일 (레포 최상위, 커밋 금지)
- token.json: 처음 로그인하면 만들어지는 토큰 파일 (레포 최상위, 커밋 금지)

같은 공지를 두 번 등록하지 않도록 일정의 비공개 속성(magami_id)에 공지 id를 넣고,
등록 전에 같은 id가 있는지 찾아본다.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = REPO_ROOT / "credentials.json"
TOKEN_PATH = REPO_ROOT / "token.json"
# 일정 만들기·찾기만 할 수 있는 권한 (다른 캘린더 설정은 건드리지 않음)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TIMEZONE = "Asia/Seoul"
EVENT_MINUTES = 30  # 마감 시각이 있으면 그 시각까지 30분짜리 일정
REMIND_MINUTES = 24 * 60  # 하루 전 알림
ID_KEY = "magami_id"


def calendar_id() -> str:
    """등록할 캘린더. .env의 GOOGLE_CALENDAR_ID가 없으면 기본 캘린더."""
    return os.environ.get("GOOGLE_CALENDAR_ID") or "primary"


def get_service(credentials_path: Path = CREDENTIALS_PATH, token_path: Path = TOKEN_PATH):
    """구글 캘린더 서비스 객체를 만든다. 처음에는 브라우저가 열려 로그인한다."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"{credentials_path} 가 없습니다. 구글 클라우드 콘솔에서 "
                    "OAuth 클라이언트 ID(데스크톱 앱) JSON을 받아 이 이름으로 넣어 주세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_path).write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------- 일정 만들기


def _description(notice: dict) -> str:
    lines = []
    start, end = notice.get("apply_start"), notice.get("apply_end")
    if start or end:
        lines.append(f"신청 기간: {start or '?'} ~ {end or '?'}")
    if notice.get("target"):
        lines.append(f"대상: {notice['target']}")
    if notice.get("how_to_apply"):
        lines.append(f"신청 방법: {notice['how_to_apply']}")
    if notice.get("url"):
        lines.append(f"원문: {notice['url']}")
    lines.append("※ 마감이가 정리한 내용입니다. 원문과 꼭 대조하세요.")
    return "\n".join(lines)


def build_event(notice: dict) -> dict:
    """공지 1건을 구글 캘린더 일정(body)으로 만든다. 마감일이 없으면 ValueError."""
    deadline = notice.get("deadline")
    if not deadline:
        raise ValueError(f"마감일이 없는 공지는 등록할 수 없습니다 (크롬 확장이나 프롬프트 방식으로 마감일을 채운 뒤 등록): {notice.get('title')!r}")
    day = date.fromisoformat(deadline)

    event = {
        "summary": f"[마감] {notice.get('title') or '제목 없음'}",
        "description": _description(notice),
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": REMIND_MINUTES}],
        },
        "extendedProperties": {"private": {ID_KEY: notice["id"]}},
    }
    if notice.get("url"):
        event["source"] = {"title": "공지 원문", "url": notice["url"]}

    time_text = notice.get("deadline_time")
    if time_text:
        hour, minute = (int(x) for x in time_text.split(":"))
        end = datetime(day.year, day.month, day.day, hour, minute)
        start = end - timedelta(minutes=EVENT_MINUTES)
        event["start"] = {"dateTime": start.isoformat(timespec="seconds"), "timeZone": TIMEZONE}
        event["end"] = {"dateTime": end.isoformat(timespec="seconds"), "timeZone": TIMEZONE}
    else:
        # 하루 종일 일정: 끝 날짜는 다음 날(구글 캘린더 규칙)
        event["start"] = {"date": day.isoformat()}
        event["end"] = {"date": (day + timedelta(days=1)).isoformat()}
    return event


# ---------------------------------------------------------------- 등록


def already_added(service, notice_id: str, cal_id: str | None = None) -> bool:
    """같은 공지 id로 등록한 일정이 있으면 True."""
    result = (
        service.events()
        .list(
            calendarId=cal_id or calendar_id(),
            privateExtendedProperty=f"{ID_KEY}={notice_id}",
            maxResults=1,
            singleEvents=True,
        )
        .execute()
    )
    return bool(result.get("items"))


def add_notice(service, notice: dict, cal_id: str | None = None) -> str:
    """공지를 캘린더에 등록한다. 이미 있으면 'exists', 새로 넣으면 'added'.

    마감일이 없으면 ValueError (캘린더에는 접속하지 않는다).
    """
    body = build_event(notice)
    cal_id = cal_id or calendar_id()
    if already_added(service, notice["id"], cal_id):
        return "exists"
    service.events().insert(calendarId=cal_id, body=body).execute()
    return "added"
