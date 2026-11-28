"""공지 1건을 Gemini로 정리해 docs/schema.md 형식의 JSON으로 만든다.

크롬 확장 프로그램·프롬프트 방식과 같은 프롬프트(prompts/extract_notice.md)를 쓴다.

사용 예 (레포 최상위 폴더에서):
    python -m magami.extract --text-file data/raw/sample.txt --url https://... --posted-at 2026-11-20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = REPO_ROOT / "prompts" / "extract_notice.md"
DEFAULT_MODEL = "gemini-2.5-flash"
KST = timezone(timedelta(hours=9))

# AI가 채우는 항목 (나머지 항목은 이 모듈이 채운다)
AI_FIELDS = (
    "is_notice",
    "title",
    "apply_start",
    "apply_end",
    "deadline",
    "deadline_time",
    "target",
    "how_to_apply",
)
SCHEMA_ORDER = (
    "id",
    "source",
    "channel",
    "url",
    "posted_at",
    *AI_FIELDS,
    "collected_at",
)
SOURCES = ("auto", "extension", "prompt")


def load_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- 값 정리

_DATE_RE = re.compile(r"^\s*(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\s*$")
_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*[:시]\s*(\d{2})?\s*분?\s*$")


def normalize_date(value) -> str | None:
    """'2026.11.3', '2026/11/03', '2026년 11월 3일' → '2026-11-03'. 해석할 수 없으면 None."""
    if value is None:
        return None
    m = _DATE_RE.match(str(value))
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def normalize_time(value) -> str | None:
    """'18:00', '9:5'(X), '18시', '18시 30분' → 'HH:MM'. 해석할 수 없으면 None."""
    if value is None:
        return None
    m = _TIME_RE.match(str(value))
    if not m:
        return None
    hour, minute = int(m[1]), int(m[2] or 0)
    if hour > 24 or minute > 59:
        return None
    if hour == 24:  # '24:00' 마감은 그날 끝으로 본다
        hour, minute = 23, 59
    return f"{hour:02d}:{minute:02d}"


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text or text.lower() in ("null", "none"):
        return None
    return text


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def parse_response(raw: str) -> dict:
    """AI 응답 문자열에서 JSON을 꺼내 AI_FIELDS만 정리해 돌려준다."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"AI 응답에서 JSON을 찾지 못했습니다: {raw[:200]!r}")
        text = text[start : end + 1]
    data = json.loads(text)

    fields = {
        "is_notice": _to_bool(data.get("is_notice")),
        "title": _clean_text(data.get("title")),
        "apply_start": normalize_date(data.get("apply_start")),
        "apply_end": normalize_date(data.get("apply_end")),
        "deadline": normalize_date(data.get("deadline")),
        "deadline_time": normalize_time(data.get("deadline_time")),
        "target": _clean_text(data.get("target")),
        "how_to_apply": _clean_text(data.get("how_to_apply")),
    }
    # 신청 기간이 있는데 마감일이 비었으면 신청 종료일을 마감일로 본다 (프롬프트 규칙 3)
    if fields["deadline"] is None and fields["apply_end"]:
        fields["deadline"] = fields["apply_end"]
    if not fields["is_notice"]:
        for key in AI_FIELDS:
            if key not in ("is_notice", "title"):
                fields[key] = None
    return fields


# ---------------------------------------------------------------- id

def make_id(url: str | None) -> str:
    """같은 공지는 어느 경로로 들어와도 같은 id가 되도록 원문 링크로 만든다."""
    if not url:
        return "unknown_" + datetime.now(KST).strftime("%Y%m%d%H%M%S")
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    query = parse_qs(parsed.query)

    if "instagram.com" in host and len(parts) >= 2 and parts[0] in ("p", "reel"):
        return f"instagram_{parts[1]}"
    if "nttSn" in query:  # 대전대학교 홈페이지 게시판 글 번호
        site = parts[0] if parts else "main"
        return f"homepage_{site}_{query['nttSn'][0]}"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"web_{digest}"


# ---------------------------------------------------------------- 조립

def make_notice(
    fields: dict,
    *,
    url: str | None,
    source: str = "prompt",
    channel: str | None = None,
    posted_at=None,
    notice_id: str | None = None,
    collected_at: datetime | None = None,
) -> dict:
    """AI가 정리한 항목에 공통 항목을 붙여 schema 순서대로 돌려준다."""
    if source not in SOURCES:
        raise ValueError(f"source는 {SOURCES} 중 하나여야 합니다: {source!r}")
    collected = (collected_at or datetime.now(KST)).astimezone(KST)
    notice = {
        "id": notice_id or make_id(url),
        "source": source,
        "channel": channel,
        "url": url,
        "posted_at": normalize_date(posted_at),
        **{key: fields.get(key) for key in AI_FIELDS},
        "collected_at": collected.isoformat(timespec="seconds"),
    }
    return {key: notice[key] for key in SCHEMA_ORDER}


def build_user_message(text: str, *, url=None, posted_at=None, today=None) -> str:
    today = today or datetime.now(KST).date().isoformat()
    lines = ["## 공지"]
    if url:
        lines.append(f"- 원문 링크: {url}")
    if posted_at:
        lines.append(f"- 게시일: {posted_at}")
    lines.append(f"- 오늘 날짜: {today}")
    lines.append("- 본문:")
    lines.append(text.strip())
    return "\n".join(lines)


def extract(
    text: str,
    *,
    url: str | None = None,
    posted_at=None,
    source: str = "prompt",
    channel: str | None = None,
    image: bytes | None = None,
    image_mime: str = "image/png",
    client=None,
    model: str | None = None,
    today: str | None = None,
) -> dict:
    """공지 본문(+이미지)을 Gemini로 정리해 schema 형식 dict를 돌려준다."""
    from google.genai import types

    if client is None:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY가 없습니다. .env 파일에 넣어 주세요.")
        client = genai.Client(api_key=api_key)

    contents: list = [build_user_message(text, url=url, posted_at=posted_at, today=today)]
    if image:
        contents.append(types.Part.from_bytes(data=image, mime_type=image_mime))

    response = client.models.generate_content(
        model=model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=load_prompt(),
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    fields = parse_response(response.text)
    return make_notice(fields, url=url, source=source, channel=channel, posted_at=posted_at)


# ---------------------------------------------------------------- 명령줄

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="공지 1건을 AI로 정리해 JSON으로 출력합니다.")
    parser.add_argument("--text-file", required=True, help="공지 본문이 담긴 텍스트 파일")
    parser.add_argument("--url", help="원문 링크")
    parser.add_argument("--posted-at", help="게시일 (YYYY-MM-DD)")
    parser.add_argument("--channel", help="채널 이름 (예: SW중심대학사업단)")
    parser.add_argument("--source", default="prompt", choices=SOURCES)
    parser.add_argument("--image", help="포스터 이미지 파일 (선택)")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    text = Path(args.text_file).read_text(encoding="utf-8")
    image = Path(args.image).read_bytes() if args.image else None
    mime = "image/jpeg" if args.image and args.image.lower().endswith((".jpg", ".jpeg")) else "image/png"
    notice = extract(
        text,
        url=args.url,
        posted_at=args.posted_at,
        source=args.source,
        channel=args.channel,
        image=image,
        image_mime=mime,
    )
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(notice, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
