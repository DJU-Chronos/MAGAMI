"""공지 체크 화면(app/streamlit_app.py) 테스트. 인터넷에는 접속하지 않는다."""

import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"

spec = importlib.util.spec_from_file_location("streamlit_app", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)  # __name__이 '__main__'이 아니라 화면은 그리지 않는다


def notice(id, **fields):
    base = {
        "id": id,
        "source": "auto",
        "channel": "SW중심대학사업단",
        "url": f"https://www.dju.ac.kr/sw/na/ntt/selectNttInfo.do?nttSn={id}",
        "posted_at": "2026-11-20",
        "is_notice": None,
        "title": f"공지 {id}",
        "deadline": None,
        "deadline_time": None,
    }
    base.update(fields)
    return base


class ParseUploadTest(unittest.TestCase):
    def test_single_object(self):
        raw = json.dumps(notice("a", deadline="2026-12-05")).encode()
        self.assertEqual([n["id"] for n in app.parse_upload(raw)], ["a"])

    def test_array_and_bom(self):
        raw = "﻿".encode() + json.dumps([notice("a"), notice("b")]).encode()
        self.assertEqual([n["id"] for n in app.parse_upload(raw)], ["a", "b"])

    def test_items_without_id_are_dropped(self):
        raw = json.dumps([notice("a"), {"title": "id 없음"}]).encode()
        self.assertEqual([n["id"] for n in app.parse_upload(raw)], ["a"])

    def test_bad_files(self):
        for raw in (b"not json", b'"text"', b"[1, 2]", b'{"title": "no id"}',"한글".encode("cp949")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                app.parse_upload(raw)


class CombineTest(unittest.TestCase):
    def test_upload_fills_deadline_and_keeps_base_fields(self):
        base = [notice("a", posted_at="2026-11-20"), notice("b")]
        upload = [{"id": "a", "source": "extension", "deadline": "2026-12-05", "deadline_time": "18:00", "posted_at": None}]
        merged = {n["id"]: n for n in app.combine(base, [upload])}
        self.assertEqual(merged["a"]["deadline"], "2026-12-05")
        self.assertEqual(merged["a"]["deadline_time"], "18:00")
        self.assertEqual(merged["a"]["source"], "extension")  # 업로드한 쪽이 이긴다
        self.assertEqual(merged["a"]["posted_at"], "2026-11-20")  # 빈 칸은 목록에서 채운다
        self.assertEqual(set(merged), {"a", "b"})

    def test_upload_only_notice_is_added(self):
        merged = app.combine([], [[notice("x", deadline="2026-12-01")]])
        self.assertEqual([n["id"] for n in merged], ["x"])

    def test_later_upload_wins(self):
        first = [notice("a", deadline="2026-12-01")]
        second = [notice("a", deadline="2026-12-03")]
        merged = app.combine([notice("a")], [first, second])
        self.assertEqual(merged[0]["deadline"], "2026-12-03")

    def test_base_is_not_changed(self):
        base = [notice("a")]
        app.combine(base, [[notice("a", deadline="2026-12-05")]])
        self.assertIsNone(base[0]["deadline"])


class VisibleTest(unittest.TestCase):
    TODAY = date(2026, 11, 28)
    NOTICES = [
        notice("unknown_old", posted_at="2026-11-01"),
        notice("later", deadline="2026-12-10"),
        notice("past", deadline="2026-11-27"),
        notice("today", deadline="2026-11-28", deadline_time="18:00"),
        notice("today_early", deadline="2026-11-28", deadline_time="09:00"),
        notice("unknown_new", posted_at="2026-11-25"),
        notice("not_notice", is_notice=False, deadline="2026-12-01"),
    ]

    def ids(self, **kw):
        return [n["id"] for n in app.visible(self.NOTICES, today=self.TODAY, **kw)]

    def test_order_and_not_notice_hidden(self):
        self.assertEqual(self.ids(), ["past", "today_early", "today", "later", "unknown_new", "unknown_old"])

    def test_only_deadline(self):
        self.assertEqual(self.ids(only_deadline=True), ["past", "today_early", "today", "later"])

    def test_hide_past_keeps_today_and_unknown(self):
        self.assertEqual(self.ids(hide_past=True), ["today_early", "today", "later", "unknown_new", "unknown_old"])

    def test_counts_skip_not_notice(self):
        self.assertEqual(app.counts(self.NOTICES), (6, 4, 2))


class TableRowsTest(unittest.TestCase):
    def test_unknown_deadline_and_checked(self):
        rows = app.table_rows([notice("a"), notice("b", deadline="2026-12-05", deadline_time="18:00")], {"b"})
        self.assertEqual(rows[0]["마감일"], "미확인")
        self.assertFalse(rows[0]["등록"])
        self.assertEqual((rows[1]["마감일"], rows[1]["시각"], rows[1]["등록"]), ("2026-12-05", "18:00", True))
        self.assertEqual(list(rows[0]), ["id", "등록", "마감일", "시각", "제목", "채널", "게시일", "원문"])


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.content = json.dumps(data, ensure_ascii=False).encode() if data is not None else b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class ScreenTest(unittest.TestCase):
    """streamlit.testing의 AppTest로 화면 전체를 돌려 본다. requests.get은 가짜로 바꾼다."""

    GITHUB_DATA = [
        notice("a", deadline="2099-12-05"),
        notice("b"),
        notice("c", deadline="2020-01-01"),
        notice("d", is_notice=False),
    ]

    def setUp(self):
        import streamlit as st
        import streamlit.logger
        from streamlit.testing.v1 import AppTest

        streamlit.logger.set_log_level("error")  # 화면 밖에서 캐시를 지울 때 나오는 경고 끄기
        st.cache_data.clear()
        self.at = AppTest.from_file(str(APP_PATH), default_timeout=30)

    def run_app(self, response):
        with mock.patch("requests.get", return_value=response) as get:
            self.at.run()
        self.assertFalse(self.at.exception, [e.value for e in self.at.exception])
        return get

    def metrics(self):
        return [m.value for m in self.at.metric]

    def test_github_source(self):
        get = self.run_app(FakeResponse(200, self.GITHUB_DATA))
        self.assertEqual(get.call_args.args[0], app.DEFAULT_URL)
        self.assertIn("원문과 꼭 대조하세요", self.at.warning[0].value)
        self.assertEqual(self.metrics(), ["3", "2", "1"])
        self.assertIn("표에 3건", self.at.caption[0].value)

    def test_github_not_collected_yet(self):
        self.run_app(FakeResponse(404))
        self.assertIn("아직 자동 수집 결과가 없습니다", self.at.info[0].value)
        self.assertEqual(self.metrics(), ["0", "0", "0"])

    def test_github_error_is_shown(self):
        self.run_app(FakeResponse(500))
        self.assertIn("불러오지 못했습니다", self.at.error[0].value)

    def test_filters(self):
        self.run_app(FakeResponse(200, self.GITHUB_DATA))
        self.at.checkbox(key="hide_past").check()
        self.run_app(FakeResponse(200, self.GITHUB_DATA))
        self.assertIn("표에 2건", self.at.caption[0].value)
        self.at.checkbox(key="only_deadline").check()
        self.run_app(FakeResponse(200, self.GITHUB_DATA))
        self.assertIn("표에 1건", self.at.caption[0].value)
        self.assertEqual(self.metrics(), ["3", "2", "1"])  # 위쪽 숫자는 필터와 상관없이 전체

    def test_local_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notices.json"
            path.write_text(json.dumps([notice("x", deadline="2099-01-01")]), encoding="utf-8")
            self.run_app(FakeResponse(404))
            self.at.radio(key="source").set_value(app.SOURCE_LOCAL)
            self.run_app(FakeResponse(404))
            self.at.text_input(key="local_path").set_value(str(path))
            get = self.run_app(FakeResponse(404))
            get.assert_not_called()
            self.assertEqual(self.metrics(), ["1", "1", "0"])

            self.at.text_input(key="local_path").set_value(str(Path(tmp) / "없는파일.json"))
            self.run_app(FakeResponse(404))
            self.assertIn("파일이 없습니다", self.at.info[0].value)


if __name__ == "__main__":
    unittest.main()
