"""공지 목록 파일(notices.json) 읽기·쓰기와 새 공지 골라내기."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}는 공지 목록(JSON 배열)이어야 합니다.")
    return data


def save(path: Path, notices: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(notices, key=lambda n: (n.get("posted_at") or "", n.get("id") or ""), reverse=True)
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], list[dict]]:
    """id 기준으로 합친다. (합친 목록, 이번에 처음 들어온 공지)를 돌려준다.

    이미 있는 공지는 비어 있던 항목만 채운다. 사용자가 확장·프롬프트로 정리한
    마감일이 자동 수집 결과(마감일 없음)로 덮어써지지 않게 하기 위해서다.
    """
    by_id = {n["id"]: dict(n) for n in existing}
    new: list[dict] = []
    for notice in incoming:
        old = by_id.get(notice["id"])
        if old is None:
            by_id[notice["id"]] = dict(notice)
            new.append(notice)
            continue
        for key, value in notice.items():
            if old.get(key) in (None, "") and value not in (None, ""):
                old[key] = value
    return list(by_id.values()), new
