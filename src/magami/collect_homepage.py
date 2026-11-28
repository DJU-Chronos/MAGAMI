"""허용된 홈페이지 메인 페이지의 최신 공지 칸에서 제목·날짜·링크를 가져온다.

요청하기 전에 robots.txt를 확인한다. 파이썬 기본 urllib.robotparser는 버전에 따라
`*`(아무 글자)와 `$`(끝) 규칙을 해석하지 못하고, 학교 robots.txt처럼 공백이 섞인 규칙
(`Disallow: / *.jpg$`)은 허용으로 잘못 판정하므로, 판정 함수를 직접 둔다.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from .extract import make_notice

# ---------------------------------------------------------------- robots.txt


def parse_robots(text: str) -> list[tuple[str, str]]:
    """robots.txt에서 `User-agent: *` 그룹의 규칙을 [('allow'|'disallow', 경로)] 목록으로 돌려준다.

    - `#` 뒤는 주석으로 보고 지운다.
    - 경로 안의 공백은 지운다. (예: 'Disallow: / *.jpg$' → '/*.jpg$')
    - 값이 빈 `Disallow:`는 '모두 허용'이라는 뜻이라 규칙에 넣지 않는다.
    """
    rules: list[tuple[str, str]] = []
    agents: list[str] = []
    in_rules = False  # 지금 그룹에서 규칙 줄이 이미 나왔는지 (그다음 User-agent는 새 그룹)

    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()

        if key == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(value)
        elif key in ("allow", "disallow"):
            in_rules = True
            path = re.sub(r"\s+", "", value)
            if "*" in agents and path:
                rules.append((key, path))
    return rules


def _rule_matches(pattern: str, path: str) -> bool:
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def robots_allows(rules: list[tuple[str, str]], path: str) -> bool:
    """경로(쿼리 포함 가능)가 허용되는지 판정한다.

    일치하는 규칙 중 가장 긴 규칙을 따르고, 길이가 같으면 Allow가 이긴다.
    일치하는 규칙이 없으면 허용이다.
    """
    best: tuple[int, bool] | None = None  # (규칙 길이, allow 여부)
    for kind, pattern in rules:
        if _rule_matches(pattern, path):
            candidate = (len(pattern), kind == "allow")
            if best is None or candidate > best:
                best = candidate
    return best is None or best[1]


# ---------------------------------------------------------------- 메인 페이지 파싱

NOTICE_LINK = "selectNttInfo.do"  # 게시글 링크 (주소만 저장하고 열지 않는다)
DEFAULT_TAB = "공지사항"
_FULL_DATE_RE = re.compile(r"^\s*(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})\s*\.?\s*$")
# 본문 미리보기·요약 칸: 이 안의 날짜(예: 신청마감 12.31)는 게시일이 아니다
_PREVIEW_CLASSES = ("txt", "con")


def _full_date(text: str) -> str | None:
    """글자 전체가 날짜일 때만 'YYYY-MM-DD'로 돌려준다."""
    m = _FULL_DATE_RE.match(text or "")
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def _month_day(month: int, day: int, today: date) -> str | None:
    """연도가 없는 '11월 23일'을 오늘 기준 가장 가까운 과거(오늘 포함) 날짜로 본다."""
    for year in (today.year, today.year - 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate <= today:
            return candidate.isoformat()
    return None


def _in_preview(tag, stop) -> bool:
    for parent in tag.parents:
        if parent is stop:
            return False
        if any(c in (parent.get("class") or []) for c in _PREVIEW_CLASSES):
            return True
    return False


def _posted_at(item, today: date) -> str | None:
    """공지 한 칸에서 게시일을 찾는다. .date 요소 → 날짜만 적힌 요소 순서."""
    for tag in item.select(".date"):
        if _in_preview(tag, item):
            continue
        month, day = tag.select_one(".month"), tag.select_one(".day")
        if month and day:
            try:
                return _month_day(int(month.get_text(strip=True)), int(day.get_text(strip=True)), today)
            except ValueError:
                return None
        found = _full_date(tag.get_text(" ", strip=True))
        if found:
            return found
    for tag in item.find_all(["p", "span", "dd", "em"]):
        if any(c in (tag.get("class") or []) for c in _PREVIEW_CLASSES) or _in_preview(tag, item):
            continue
        found = _full_date(tag.get_text(" ", strip=True))
        if found:
            return found
    return None


def _title(link) -> str | None:
    """제목: dt → p.tit → 링크 글자(날짜만 적힌 부분은 뺌) 순서."""
    for selector in ("dt", ".tit"):
        tag = link.select_one(selector)
        if tag and tag.get_text(strip=True):
            return " ".join(tag.get_text(" ", strip=True).split())
    parts = []
    for child in link.children:
        if getattr(child, "name", None) is None:
            parts.append(str(child))
        elif not _full_date(child.get_text(" ", strip=True)):
            parts.append(child.get_text(" ", strip=True))
    text = " ".join(" ".join(parts).split())
    return text or None


def _notice_box(soup, tab: str):
    """제목이 tab인 h2/h3 바로 다음의 div.list_box."""
    for heading in soup.find_all(["h2", "h3"]):
        if heading.get_text(strip=True) == tab:
            return heading.find_next("div", class_="list_box")
    return None


def parse_main_page(html: str, base_url: str, channel: str, tab: str = DEFAULT_TAB, today: date | None = None) -> list[dict]:
    """메인 페이지 HTML에서 tab 칸의 공지 목록을 docs/schema.md 형식으로 돌려준다.

    제목·게시일·원문 링크만 채운다. 공지인지(is_notice)와 마감일 등은 본문을 정리하기
    전까지 알 수 없으므로 비워 둔다(None). 칸을 찾지 못하면 ValueError.
    """
    from bs4 import BeautifulSoup

    today = today or date.today()
    soup = BeautifulSoup(html, "html.parser")
    box = _notice_box(soup, tab)
    if box is None:
        raise ValueError(f"메인 페이지에서 '{tab}' 칸을 찾지 못했습니다: {base_url}")

    notices, seen = [], set()
    for link in box.find_all("a", href=True):
        href = link["href"].replace("&amp;", "&")
        if NOTICE_LINK not in href:
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        item = link.find_parent("li") or link.find_parent(class_="top_list") or link
        notices.append(
            make_notice(
                {"title": _title(link), "is_notice": None},
                url=url,
                source="auto",
                channel=channel,
                posted_at=_posted_at(item, today),
            )
        )
    return notices
