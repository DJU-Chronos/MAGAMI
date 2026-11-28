"""extract.py 단위 테스트 (Gemini는 가짜 객체로 대신해 인터넷 없이 실행된다).

실행: python -m unittest discover -s tests
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from magami import extract as ex  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(ex.normalize_date("2026-11-03"), "2026-11-03")
        self.assertEqual(ex.normalize_date("2026.11.3"), "2026-11-03")
        self.assertEqual(ex.normalize_date("2026/11/03"), "2026-11-03")
        self.assertEqual(ex.normalize_date("2026년 11월 3일"), "2026-11-03")
        self.assertIsNone(ex.normalize_date("2026-02-30"))
        self.assertIsNone(ex.normalize_date("11월 3일"))
        self.assertIsNone(ex.normalize_date(None))

    def test_times(self):
        self.assertEqual(ex.normalize_time("18:00"), "18:00")
        self.assertEqual(ex.normalize_time("9:05"), "09:05")
        self.assertEqual(ex.normalize_time("18시"), "18:00")
        self.assertEqual(ex.normalize_time("18시 30분"), "18:30")
        self.assertEqual(ex.normalize_time("24:00"), "23:59")
        self.assertIsNone(ex.normalize_time("25:00"))
        self.assertIsNone(ex.normalize_time("오후 6시"))


class ParseResponseTest(unittest.TestCase):
    def test_plain_json(self):
        fields = ex.parse_response(
            '{"is_notice": true, "title": " 공모전 ", "apply_start": "2026.11.01",'
            ' "apply_end": "2026-11-30", "deadline": null, "deadline_time": "18시",'
            ' "target": "재학생", "how_to_apply": "null"}'
        )
        self.assertTrue(fields["is_notice"])
        self.assertEqual(fields["title"], "공모전")
        self.assertEqual(fields["apply_start"], "2026-11-01")
        # 마감일이 비면 신청 종료일을 쓴다
        self.assertEqual(fields["deadline"], "2026-11-30")
        self.assertEqual(fields["deadline_time"], "18:00")
        self.assertIsNone(fields["how_to_apply"])

    def test_code_fence(self):
        fields = ex.parse_response('```json\n{"is_notice": true, "title": "a", "deadline": "2026-12-01"}\n```')
        self.assertEqual(fields["deadline"], "2026-12-01")

    def test_not_notice_clears_dates(self):
        fields = ex.parse_response('{"is_notice": false, "title": "홍보 영상", "deadline": "2026-12-01"}')
        self.assertFalse(fields["is_notice"])
        self.assertEqual(fields["title"], "홍보 영상")
        self.assertIsNone(fields["deadline"])

    def test_no_json(self):
        with self.assertRaises(ValueError):
            ex.parse_response("정리할 수 없습니다")


class MakeIdTest(unittest.TestCase):
    def test_homepage(self):
        url = "https://www.dju.ac.kr/sw/na/ntt/selectNttInfo.do?mi=1&nttSn=12345"
        self.assertEqual(ex.make_id(url), "homepage_sw_12345")

    def test_instagram(self):
        self.assertEqual(ex.make_id("https://www.instagram.com/p/ABC123/"), "instagram_ABC123")

    def test_other_is_stable(self):
        url = "https://example.com/notice/1"
        self.assertEqual(ex.make_id(url), ex.make_id(url))
        self.assertTrue(ex.make_id(url).startswith("web_"))


class MakeNoticeTest(unittest.TestCase):
    def test_schema_order_and_values(self):
        fields = {"is_notice": True, "title": "t", "deadline": "2026-12-01"}
        notice = ex.make_notice(
            fields,
            url="https://www.instagram.com/p/X1/",
            source="extension",
            channel="@daejeon_univ",
            posted_at="2026.11.20",
            collected_at=datetime(2026, 11, 27, 0, 0),
        )
        self.assertEqual(tuple(notice), ex.SCHEMA_ORDER)
        self.assertEqual(notice["id"], "instagram_X1")
        self.assertEqual(notice["posted_at"], "2026-11-20")
        self.assertIsNone(notice["apply_start"])
        self.assertTrue(notice["collected_at"].endswith("+09:00"))

    def test_bad_source(self):
        with self.assertRaises(ValueError):
            ex.make_notice({}, url=None, source="instagram")


class ExtractWithFakeClientTest(unittest.TestCase):
    def test_extract_uses_shared_prompt(self):
        calls = {}

        def generate_content(model, contents, config):
            calls.update(model=model, contents=contents, config=config)
            return SimpleNamespace(
                text='{"is_notice": true, "title": "해커톤", "apply_end": "2026-12-05"}'
            )

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        notice = ex.extract(
            "12월 5일까지 신청",
            url="https://example.com/a",
            posted_at="2026-11-25",
            source="prompt",
            client=client,
            model="test-model",
            today="2026-11-27",
        )
        self.assertEqual(notice["deadline"], "2026-12-05")
        self.assertEqual(calls["model"], "test-model")
        self.assertEqual(calls["config"].system_instruction, ex.load_prompt())
        self.assertIn("오늘 날짜: 2026-11-27", calls["contents"][0])


class PromptFileTest(unittest.TestCase):
    def test_prompt_lists_all_ai_fields(self):
        prompt = ex.load_prompt()
        for key in ex.AI_FIELDS:
            self.assertIn(f'"{key}"', prompt)


if __name__ == "__main__":
    unittest.main()
