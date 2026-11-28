"""하루 1회 자동 실행: 메인 공지 칸 수집 → 목록 저장 → 새 공지 이메일 알림.

GitHub Actions(.github/workflows/daily.yml)가 매일 실행한다. 직접 실행할 때:
    python -m magami.daily --store data/notices.json --dry-run

수집기는 src/magami/collect_homepage.py의 collect(channel) 함수를 쓴다.
    collect(channel: dict) -> list[dict]
    - channel: config/channels.yaml의 homepages 항목 하나 (name, url, ...)
    - 돌려주는 값: docs/schema.md 형식의 공지 목록 (source="auto", 제목·날짜·링크만)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import notify, store

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNELS_PATH = REPO_ROOT / "config" / "channels.yaml"


def load_channels(path: Path = CHANNELS_PATH) -> list[dict]:
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    homepages = data.get("homepages") or []
    return [c for c in homepages if c.get("enabled") and c.get("robots_allowed")]


def collect_all(channels: list[dict], collect) -> tuple[list[dict], list[str]]:
    """채널 하나가 실패해도 나머지는 계속 수집한다."""
    notices, errors = [], []
    for channel in channels:
        try:
            notices.extend(collect(channel))
        except Exception as exc:  # noqa: BLE001 - 채널별 오류를 기록하고 계속
            errors.append(f"{channel.get('name')}: {exc}")
    return notices, errors


def run(store_path: Path, *, dry_run: bool = False, collect=None, channels=None) -> int:
    if collect is None:
        try:
            from .collect_homepage import collect
        except ImportError:
            print("수집기(src/magami/collect_homepage.py)가 아직 없습니다. 수집을 건너뜁니다.")
            return 0
    channels = load_channels() if channels is None else channels
    if not channels:
        print("수집할 채널이 없습니다. config/channels.yaml에서 enabled·robots_allowed를 확인하세요.")
        return 0

    incoming, errors = collect_all(channels, collect)
    merged, new = store.merge(store.load(store_path), incoming)
    print(f"채널 {len(channels)}곳 · 가져온 공지 {len(incoming)}건 · 새 공지 {len(new)}건")
    for err in errors:
        print(f"[오류] {err}")

    if dry_run:
        for n in new:
            print(f"  NEW {n.get('channel')} | {n.get('title')} | {n.get('url')}")
        return 0

    store.save(store_path, merged)
    if notify.send(new):
        print("새 공지 이메일을 보냈습니다.")
    # 모든 채널이 실패했을 때만 실패로 끝내서 Actions에 빨간 표시가 나게 한다
    return 1 if errors and len(errors) == len(channels) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="메인 공지 칸을 수집하고 새 공지를 알립니다.")
    parser.add_argument("--store", default=str(REPO_ROOT / "data" / "notices.json"))
    parser.add_argument("--dry-run", action="store_true", help="저장·알림 없이 결과만 출력")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    return run(Path(args.store), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
