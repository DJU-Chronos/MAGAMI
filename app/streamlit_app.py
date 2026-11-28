"""공지 체크 화면: 공지 목록을 원문 링크와 함께 보여 주고, 캘린더에 넣을 공지를 체크한다.

실행:
    streamlit run app/streamlit_app.py

- 목록: GitHub data 브랜치(매일 자동 수집 결과) 또는 내 컴퓨터 data/notices.json
- 크롬 확장에서 저장한 JSON을 올리면 같은 id 공지의 마감일이 채워진다.
- 마감일이 없는 공지는 "미확인"으로 보여 준다.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from magami import store
except ImportError:  # pip install -e . 을 하지 않고 실행한 경우
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from magami import store

DEFAULT_URL = "https://raw.githubusercontent.com/DJU-Chronos/MAGAMI/data/notices.json"
DEFAULT_LOCAL = REPO_ROOT / "data" / "notices.json"
SOURCE_GITHUB = "GitHub 자동 수집 (data 브랜치)"
SOURCE_LOCAL = "내 컴퓨터 파일"
KST = timezone(timedelta(hours=9))
UNKNOWN = "미확인"

# ---------------------------------------------------------------- 화면과 상관없는 처리 (테스트 대상)


def today_kst() -> date:
    return datetime.now(KST).date()


def parse_upload(raw: bytes) -> list[dict]:
    """크롬 확장 JSON 한 파일을 공지 목록으로 바꾼다.

    공지 1건(객체)과 여러 건(배열) 모두 받는다. id가 없는 항목은 뺀다.
    형식이 틀리면 ValueError.
    """
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON 파일이 아닙니다 ({exc})") from exc
    items = data if isinstance(data, list) else [data]
    if not all(isinstance(n, dict) for n in items):
        raise ValueError("공지(객체) 또는 공지 목록(배열)이어야 합니다")
    notices = [n for n in items if n.get("id")]
    if not notices:
        raise ValueError("id가 있는 공지가 없습니다")
    return notices


def combine(base: list[dict], uploads: list[list[dict]]) -> list[dict]:
    """목록과 업로드한 파일들을 id 기준으로 합친다.

    업로드한 쪽 값이 이긴다(나중에 올린 파일일수록 우선). 비어 있는 칸만 다른 쪽에서 채운다.
    """
    extension: list[dict] = []
    for notices in uploads:
        extension = store.merge(notices, extension)[0]
    return store.merge(extension, base)[0]


def visible(notices: list[dict], *, only_deadline: bool = False, hide_past: bool = False, today: date | None = None) -> list[dict]:
    """표에 보일 공지. 공지가 아니라고 정리된 글(is_notice false)은 항상 숨긴다."""
    today_iso = (today or today_kst()).isoformat()
    shown = []
    for n in notices:
        if n.get("is_notice") is False:
            continue
        deadline = n.get("deadline")
        if only_deadline and not deadline:
            continue
        if hide_past and deadline and deadline < today_iso:
            continue
        shown.append(n)
    # 마감이 가까운 순, 마감일 미확인은 아래에 최근 게시일 순
    with_deadline = sorted((n for n in shown if n.get("deadline")), key=lambda n: (n["deadline"], n.get("deadline_time") or "99:99"))
    without = sorted((n for n in shown if not n.get("deadline")), key=lambda n: n.get("posted_at") or "", reverse=True)
    return with_deadline + without


def counts(notices: list[dict]) -> tuple[int, int, int]:
    """(공지 수, 마감일 확인됨, 미확인). is_notice false는 세지 않는다."""
    notices = [n for n in notices if n.get("is_notice") is not False]
    known = sum(1 for n in notices if n.get("deadline"))
    return len(notices), known, len(notices) - known


def table_rows(notices: list[dict], checked: set[str]) -> list[dict]:
    return [
        {
            "id": n["id"],
            "등록": n["id"] in checked,
            "마감일": n.get("deadline") or UNKNOWN,
            "시각": n.get("deadline_time") or "",
            "제목": n.get("title") or "(제목 없음)",
            "채널": n.get("channel") or "",
            "게시일": n.get("posted_at") or "",
            "원문": n.get("url") or "",
        }
        for n in notices
    ]


# ---------------------------------------------------------------- 목록 불러오기


def fetch_github(url: str) -> list[dict] | None:
    """data 브랜치의 notices.json. 아직 없으면(404) None."""
    import requests

    res = requests.get(url, timeout=15)
    if res.status_code == 404:
        return None
    res.raise_for_status()
    data = json.loads(res.content.decode("utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("공지 목록(JSON 배열)이 아닙니다")
    return data


# ---------------------------------------------------------------- 화면


def main() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="마감이 공지 체크", page_icon="📅", layout="wide")

    @st.cache_data(ttl=600, show_spinner="GitHub에서 공지 목록을 가져오는 중...")
    def cached_github(url: str):
        return fetch_github(url)

    st.title("📅 마감이 공지 체크")
    st.warning("마감일·시각은 AI가 정리한 값이라 틀릴 수 있습니다. 캘린더에 넣기 전에 **원문과 꼭 대조하세요.**")

    # ---- 왼쪽 메뉴
    with st.sidebar:
        st.header("공지 목록")
        source = st.radio("어디서 불러올까요?", [SOURCE_GITHUB, SOURCE_LOCAL], key="source")
        if source == SOURCE_GITHUB:
            url = st.text_input("data 브랜치 notices.json 주소", DEFAULT_URL, key="github_url",
                                help="fork한 레포라면 주소의 DJU-Chronos/MAGAMI를 내 레포로 바꾸세요.")
            if st.button("새로 가져오기"):
                cached_github.clear()
        else:
            local_path = st.text_input("파일 위치", str(DEFAULT_LOCAL), key="local_path")

        st.header("크롬 확장 JSON")
        files = st.file_uploader("확장에서 저장한 JSON (여러 개 가능)", type="json", accept_multiple_files=True)

        st.header("보기")
        only_deadline = st.checkbox("마감일 있는 공지만", key="only_deadline")
        hide_past = st.checkbox("마감 지난 공지 숨기기", key="hide_past")

    # ---- 목록 불러오기
    base: list[dict] = []
    try:
        if source == SOURCE_GITHUB:
            fetched = cached_github(url)
            if fetched is None:
                st.info("GitHub에 아직 자동 수집 결과가 없습니다. 레포 Actions에서 '매일 공지 수집'을 한 번 실행하거나, 크롬 확장 JSON을 올려 보세요.")
            else:
                base = fetched
        else:
            path = Path(local_path)
            if path.exists():
                base = store.load(path)
            else:
                st.info(f"{path} 파일이 없습니다. `python -m magami.daily`로 수집하거나, 크롬 확장 JSON을 올려 보세요.")
    except Exception as exc:  # noqa: BLE001 - 화면에 알리고 업로드만으로도 쓸 수 있게
        st.error(f"공지 목록을 불러오지 못했습니다: {exc}")

    uploads = []
    for f in files or []:
        try:
            uploads.append(parse_upload(f.getvalue()))
        except ValueError as exc:
            st.warning(f"{f.name}: {exc} — 이 파일은 건너뜁니다.")
    notices = combine(base, uploads)
    if uploads:
        st.success(f"확장 JSON {len(uploads)}개 ({sum(len(u) for u in uploads)}건)를 목록에 합쳤습니다.")

    # ---- 숫자
    total, known, unknown = counts(notices)
    c1, c2, c3 = st.columns(3)
    c1.metric("공지 수", total)
    c2.metric("마감일 확인됨", known)
    c3.metric("마감일 미확인", unknown)

    # ---- 표
    shown = visible(notices, only_deadline=only_deadline, hide_past=hide_past)
    if not shown:
        st.write("보여 줄 공지가 없습니다.")
        return

    checked: set[str] = st.session_state.setdefault("checked", set())
    df = pd.DataFrame(table_rows(shown, checked)).set_index("id")
    edited = st.data_editor(
        df,
        key="table_" + str(hash(tuple(df.index))),
        hide_index=True,
        disabled=[c for c in df.columns if c != "등록"],
        column_config={
            "등록": st.column_config.CheckboxColumn("등록", help="캘린더에 넣을 공지를 체크하세요", width="small"),
            "시각": st.column_config.TextColumn("시각", width="small"),
            "제목": st.column_config.TextColumn("제목", width="large"),
            "원문": st.column_config.LinkColumn("원문", display_text="열기", width="small"),
        },
    )
    # 필터를 바꿔도 체크가 남도록, 지금 보이는 줄만 갱신한다
    checked -= set(df.index)
    checked |= set(edited.index[edited["등록"]])

    st.caption(f"표에 {len(shown)}건 · 체크한 공지 {len(checked)}건 · 마감일 미확인 공지는 원문을 열어 크롬 확장으로 정리한 뒤 JSON을 올리세요.")


if __name__ == "__main__":
    main()
