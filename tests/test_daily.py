"""store · notify · daily 단위 테스트 (네트워크·메일 서버 없이 실행)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from magami import daily, notify, store  # noqa: E402


def notice(id_, **kw):
    base = {"id": id_, "source": "auto", "channel": "SW", "url": f"https://x/{id_}",
            "posted_at": "2026-11-27", "title": f"공지 {id_}", "deadline": None}
    base.update(kw)
    return base


class StoreTest(unittest.TestCase):
    def test_merge_returns_only_new(self):
        merged, new = store.merge([notice("a")], [notice("a"), notice("b")])
        self.assertEqual([n["id"] for n in new], ["b"])
        self.assertEqual(len(merged), 2)

    def test_merge_keeps_user_deadline(self):
        existing = [notice("a", deadline="2026-12-05", source="extension")]
        merged, _ = store.merge(existing, [notice("a", deadline=None)])
        self.assertEqual(merged[0]["deadline"], "2026-12-05")
        self.assertEqual(merged[0]["source"], "extension")

    def test_merge_fills_empty_fields(self):
        merged, _ = store.merge([notice("a", posted_at=None)], [notice("a")])
        self.assertEqual(merged[0]["posted_at"], "2026-11-27")

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "notices.json"
            self.assertEqual(store.load(path), [])
            store.save(path, [notice("a"), notice("b", posted_at="2026-11-28")])
            loaded = store.load(path)
            self.assertEqual([n["id"] for n in loaded], ["b", "a"])  # 최신순


class FakeSMTP:
    sent = []

    def __init__(self, host, port):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, password):
        self.user = user

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


class NotifyTest(unittest.TestCase):
    settings = {"user": "bot@gmail.com", "password": "x", "to": ["me@example.com"]}

    def setUp(self):
        FakeSMTP.sent = []

    def test_no_new_no_mail(self):
        self.assertFalse(notify.send([], self.settings, smtp_factory=FakeSMTP))
        self.assertEqual(FakeSMTP.sent, [])

    def test_sends_with_link_and_deadline_hint(self):
        ok = notify.send([notice("a"), notice("b", deadline="2026-12-01")], self.settings, smtp_factory=FakeSMTP)
        self.assertTrue(ok)
        body = FakeSMTP.sent[0].get_content()
        self.assertIn("새 공지 2건", FakeSMTP.sent[0]["Subject"])
        self.assertIn("https://x/a", body)
        self.assertIn("마감일 미확인", body)
        self.assertIn("마감: 2026-12-01", body)

    def test_missing_settings_skips(self):
        import os
        saved = {k: os.environ.pop(k, None) for k in ("SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO")}
        try:
            self.assertIsNone(notify.settings_from_env())
            self.assertFalse(notify.send([notice("a")], smtp_factory=FakeSMTP))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


class DailyTest(unittest.TestCase):
    def test_run_saves_and_reports_new(self):
        channels = [{"name": "SW", "url": "https://x", "enabled": True, "robots_allowed": True}]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "notices.json"
            store.save(path, [notice("old")])
            code = daily.run(path, collect=lambda ch: [notice("old"), notice("new")], channels=channels)
            self.assertEqual(code, 0)
            self.assertEqual({n["id"] for n in store.load(path)}, {"old", "new"})

    def test_one_channel_error_does_not_stop_others(self):
        def collect(ch):
            if ch["name"] == "bad":
                raise RuntimeError("timeout")
            return [notice("ok")]

        notices, errors = daily.collect_all([{"name": "bad"}, {"name": "good"}], collect)
        self.assertEqual([n["id"] for n in notices], ["ok"])
        self.assertEqual(len(errors), 1)

    def test_all_channels_fail_returns_1(self):
        def collect(ch):
            raise RuntimeError("down")

        with tempfile.TemporaryDirectory() as d:
            code = daily.run(Path(d) / "n.json", collect=collect, channels=[{"name": "a"}])
            self.assertEqual(code, 1)

    def test_load_channels_filters_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.yaml"
            p.write_text(
                "homepages:\n"
                "  - {name: a, url: 'https://a', robots_allowed: true, enabled: true}\n"
                "  - {name: b, url: 'https://b', robots_allowed: false, enabled: true}\n"
                "  - {name: c, url: 'https://c', robots_allowed: true, enabled: false}\n",
                encoding="utf-8",
            )
            self.assertEqual([c["name"] for c in daily.load_channels(p)], ["a"])


if __name__ == "__main__":
    unittest.main()
