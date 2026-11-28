"""새 공지 이메일 알림 (Gmail SMTP + 앱 비밀번호).

필요한 환경 변수 (GitHub Actions에서는 Secrets):
    SMTP_USER       보내는 Gmail 주소
    SMTP_PASSWORD   Gmail 앱 비밀번호 16자리 (일반 비밀번호 아님)
    ALERT_EMAIL_TO  받는 주소 (쉼표로 여러 개)
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def settings_from_env() -> dict | None:
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
    to = [a.strip() for a in os.environ.get("ALERT_EMAIL_TO", "").split(",") if a.strip()]
    if not (user and password and to):
        return None
    return {"user": user, "password": password, "to": to}


def build_message(new_notices: list[dict], *, sender: str, to: list[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"[마감이] 새 공지 {len(new_notices)}건"
    msg["From"] = sender
    msg["To"] = ", ".join(to)

    lines = [f"새 공지 {len(new_notices)}건이 올라왔습니다.", ""]
    for n in new_notices:
        date = n.get("posted_at") or "날짜 없음"
        lines.append(f"■ [{n.get('channel') or '채널'}] {n.get('title') or '(제목 없음)'} ({date})")
        if n.get("deadline"):
            lines.append(f"   마감: {n['deadline']}" + (f" {n['deadline_time']}" if n.get("deadline_time") else ""))
        else:
            lines.append("   마감일 미확인 — 원문을 열고 크롬 확장 '이 공지 정리하기'로 확인하세요.")
        lines.append(f"   {n.get('url')}")
        lines.append("")
    lines.append("— 마감이 (https://github.com/DJU-Chronos/MAGAMI)")
    msg.set_content("\n".join(lines))
    return msg


def send(new_notices: list[dict], settings: dict | None = None, smtp_factory=smtplib.SMTP_SSL) -> bool:
    """보냈으면 True. 새 공지가 없거나 설정이 없으면 보내지 않고 False."""
    if not new_notices:
        return False
    settings = settings or settings_from_env()
    if settings is None:
        print("이메일 설정(SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO)이 없어 알림을 건너뜁니다.")
        return False
    msg = build_message(new_notices, sender=settings["user"], to=settings["to"])
    with smtp_factory(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(settings["user"], settings["password"])
        smtp.send_message(msg)
    return True
