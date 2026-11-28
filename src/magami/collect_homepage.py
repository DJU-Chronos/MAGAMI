"""허용된 홈페이지 메인 페이지의 최신 공지 칸에서 제목·날짜·링크를 가져온다.

요청하기 전에 robots.txt를 확인한다. 파이썬 기본 urllib.robotparser는 버전에 따라
`*`(아무 글자)와 `$`(끝) 규칙을 해석하지 못하고, 학교 robots.txt처럼 공백이 섞인 규칙
(`Disallow: / *.jpg$`)은 허용으로 잘못 판정하므로, 판정 함수를 직접 둔다.
"""

from __future__ import annotations

import re

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
