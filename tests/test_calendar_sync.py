"""calendar_sync.py 단위 테스트 (가짜 캘린더 서비스로 대신해 구글에 접속하지 않는다).

실행: python -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from magami import calendar_sync as cs  # noqa: E402


def make_notice(**overrides):
    notice = {
        "id": "homepage_sw_555675",
        "source": "auto",
        "channel": "SW중심대학사업단",
        "url": "https://www.dju.ac.kr/sw/na/ntt/selectNttInfo.do?nttSn=555675",
        "posted_at": "2026-11-20",
        "is_notice": True,
        "title": "SW 공모전 참가자 모집",
        "apply_start": "2026-11-20",
        "apply_end": "2026-12-05",
        "deadline": "2026-12-05",
        "deadline_time": "18:00",
        "target": "재학생",
        "how_to_apply": "신청서 작성 후 이메일 제출",
        "collected_at": "2026-11-28T09:00:00+09:00",
    }
    notice.update(overrides)
    return notice


class _Request:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class FakeEvents:
    """events().list / events().insert 만 흉내 낸다."""

    def __init__(self, store):
        self.store = store

    def list(self, calendarId, privateExtendedProperty=None, **kwargs):
        key, value = privateExtendedProperty.split("=", 1)
        self.store["list_calls"].append((calendarId, privateExtendedProperty))
        items = [
            e for e in self.store["events"]
            if e["extendedProperties"]["private"].get(key) == value
        ]
        return _Request({"items": items[: kwargs.get("maxResults", 250)]})

    def insert(self, calendarId, body):
        self.store["events"].append(body)
        self.store["insert_calls"].append(calendarId)
        return _Request({"id": f"evt{len(self.store['events'])}", **body})


class FakeService:
    def __init__(self):
        self.store = {"events": [], "list_calls": [], "insert_calls": []}

    def events(self):
        return FakeEvents(self.store)


class BuildEventTest(unittest.TestCase):
    def test_timed_event(self):
        event = cs.build_event(make_notice())
        self.assertEqual(event["summary"], "[마감] SW 공모전 참가자 모집")
        self.assertEqual(event["start"], {"dateTime": "2026-12-05T17:30:00", "timeZone": "Asia/Seoul"})
        self.assertEqual(event["end"], {"dateTime": "2026-12-05T18:00:00", "timeZone": "Asia/Seoul"})
        self.assertEqual(event["extendedProperties"]["private"]["magami_id"], "homepage_sw_555675")
        self.assertEqual(event["reminders"]["overrides"], [{"method": "popup", "minutes": 1440}])
        for text in ("신청 기간: 2026-11-20 ~ 2026-12-05", "대상: 재학생",
                     "신청 방법: 신청서 작성 후 이메일 제출", "원문: https://www.dju.ac.kr/"):
            self.assertIn(text, event["description"])

    def test_all_day_event_without_time(self):
        event = cs.build_event(make_notice(deadline_time=None))
        self.assertEqual(event["start"], {"date": "2026-12-05"})
        self.assertEqual(event["end"], {"date": "2026-12-06"})

    def test_early_morning_deadline_starts_previous_day(self):
        event = cs.build_event(make_notice(deadline="2026-12-01", deadline_time="00:10"))
        self.assertEqual(event["start"]["dateTime"], "2026-11-30T23:40:00")

    def test_month_end_all_day(self):
        event = cs.build_event(make_notice(deadline="2026-12-31", deadline_time=None))
        self.assertEqual(event["end"], {"date": "2027-01-01"})

    def test_missing_fields_are_skipped(self):
        event = cs.build_event(make_notice(apply_start=None, apply_end=None, target=None, how_to_apply=None))
        self.assertNotIn("신청 기간", event["description"])
        self.assertNotIn("대상", event["description"])
        self.assertIn("원문:", event["description"])

    def test_no_deadline_raises(self):
        with self.assertRaises(ValueError):
            cs.build_event(make_notice(deadline=None))


class AddNoticeTest(unittest.TestCase):
    def test_add_then_exists(self):
        service = FakeService()
        self.assertEqual(cs.add_notice(service, make_notice(), "primary"), "added")
        self.assertEqual(cs.add_notice(service, make_notice(), "primary"), "exists")
        self.assertEqual(len(service.store["events"]), 1)
        self.assertEqual(service.store["list_calls"][0], ("primary", "magami_id=homepage_sw_555675"))

    def test_different_notice_is_added(self):
        service = FakeService()
        cs.add_notice(service, make_notice(), "primary")
        self.assertEqual(cs.add_notice(service, make_notice(id="homepage_sw_1"), "primary"), "added")
        self.assertEqual(len(service.store["events"]), 2)

    def test_no_deadline_does_not_touch_calendar(self):
        service = FakeService()
        with self.assertRaises(ValueError):
            cs.add_notice(service, make_notice(deadline=None), "primary")
        self.assertEqual(service.store["list_calls"], [])
        self.assertEqual(service.store["insert_calls"], [])

    def test_calendar_id_from_env(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"GOOGLE_CALENDAR_ID": "team@group.calendar.google.com"}):
            self.assertEqual(cs.calendar_id(), "team@group.calendar.google.com")
        with mock.patch.dict(os.environ, {"GOOGLE_CALENDAR_ID": ""}):
            self.assertEqual(cs.calendar_id(), "primary")


class GetServiceTest(unittest.TestCase):
    def test_missing_credentials_message(self):
        tmp = Path(__file__).resolve().parent / "_no_such_dir"
        with self.assertRaises(FileNotFoundError) as ctx:
            cs.get_service(tmp / "credentials.json", tmp / "token.json")
        self.assertIn("credentials.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
