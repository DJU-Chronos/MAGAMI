"""collect_homepage.py 단위 테스트 (인터넷 없이 실행된다).

실행: python -m unittest discover -s tests
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from magami import collect_homepage as ch  # noqa: E402

# www.dju.ac.kr/robots.txt (2026-11-28 확인) 내용
DJU_ROBOTS = """User-agent: *

Disallow: / *.jpg$
Disallow: / *.png$
Disallow: / *.gif$
Disallow: / *.pdf$
Disallow: / *.ppt$
Disallow: / *.pptx$
Disallow: / *.xls$
Disallow: / *.xlsx$
Disallow: / *.doc$
Disallow: / *.docx$
Disallow: / *.hwp$
Disallow: /*/na/ntt/
Disallow: /*/cm/cntnts/
Disallow: /*/cp/cttpc/
Disallow: /*/depart/
Allow: /$
Sitemap: https://www.dju.ac.kr/sitemap.xml"""


class ParseRobotsTest(unittest.TestCase):
    def test_school_robots(self):
        rules = ch.parse_robots(DJU_ROBOTS)
        self.assertEqual(len(rules), 16)
        self.assertIn(("disallow", "/*.jpg$"), rules)  # 공백이 섞인 규칙
        self.assertIn(("disallow", "/*/na/ntt/"), rules)
        self.assertIn(("allow", "/$"), rules)

    def test_only_star_group(self):
        text = "User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nDisallow: /private/\n"
        self.assertEqual(ch.parse_robots(text), [("disallow", "/private/")])

    def test_grouped_agents_and_comments(self):
        text = "User-agent: Bingbot\nUser-agent: *  # 모든 로봇\nDisallow: /a/ # 주석\nDisallow:\n"
        self.assertEqual(ch.parse_robots(text), [("disallow", "/a/")])


class RobotsAllowsTest(unittest.TestCase):
    def setUp(self):
        self.rules = ch.parse_robots(DJU_ROBOTS)

    def test_main_pages_allowed(self):
        for site in ("sw", "djurise", "inno", "hrd", "biohealth", "IoTCOSS"):
            self.assertTrue(ch.robots_allows(self.rules, f"/{site}/main.do"), site)
        self.assertTrue(ch.robots_allows(self.rules, "/"))

    def test_board_pages_blocked(self):
        self.assertFalse(ch.robots_allows(self.rules, "/sw/na/ntt/selectNttList.do"))
        self.assertFalse(
            ch.robots_allows(self.rules, "/sw/na/ntt/selectNttInfo.do?nttSn=555675&mi=7358")
        )

    def test_depart_and_files_blocked(self):
        self.assertFalse(ch.robots_allows(self.rules, "/comeng2/depart/main.do"))
        self.assertFalse(ch.robots_allows(self.rules, "/sw/img/poster.jpg"))
        # '$'는 끝이라는 뜻: .jpg 뒤에 글자가 더 있으면 해당하지 않는다
        self.assertTrue(ch.robots_allows(self.rules, "/sw/img/poster.jpg.do"))

    def test_longest_rule_wins_and_tie_allows(self):
        rules = [("disallow", "/a/"), ("allow", "/a/b/")]
        self.assertTrue(ch.robots_allows(rules, "/a/b/c"))
        self.assertFalse(ch.robots_allows(rules, "/a/x"))
        self.assertTrue(ch.robots_allows([("disallow", "/a"), ("allow", "/a")], "/a"))

    def test_no_rules_allows(self):
        self.assertTrue(ch.robots_allows([], "/anything"))


# ---------------------------------------------------------------- 메인 페이지 파싱
# 실제 사업단 메인 페이지 구조를 흉내 낸 가짜 HTML (네 가지 날짜 표시 방식)

BASE = "https://www.dju.ac.kr/sw/main.do"
TODAY = date(2026, 11, 28)

# ① 링크 옆 <p class="date">YYYY-MM-DD</p>
PAGE_DATE_CLASS = """
<div class="A04_NoticeBox tabBox">
  <h3 class="tit_1"><a class="current" href="#">공지사항</a></h3>
  <div class="list_box on"><ul>
    <li><a href="/sw/na/ntt/selectNttInfo.do?nttSn=555675&amp;mi=7358&amp;bbsId=2758">
        ★[SW중심대학사업단] 공간 사용 신청서 양식★
      </a><p class="date">2026-11-26</p></li>
    <li><a href="/sw/na/ntt/selectNttInfo.do?nttSn=555459&amp;mi=7358&amp;bbsId=2758">
        [SW중심대학사업단] 아이디어 공모전 개최 안내</a><p class="date">2026-11-17</p></li>
  </ul>
  <a class="btn_more" href="/sw/na/ntt/selectNttList.do?bbsId=2758&amp;mi=7358">공지사항 more</a>
  </div>
  <h3 class="tit_2"><a href="#">자료실</a></h3>
  <div class="list_box"><ul>
    <li><a href="/sw/na/ntt/selectNttInfo.do?nttSn=1&amp;mi=1">자료실 글</a><p class="date">2026-01-01</p></li>
  </ul></div>
</div>
"""

# ② 맨 위 강조 글: dt 제목 + .txt 미리보기 + <span class="month/day"> (연도 없음)
#    목록 글: 제목<p>YYYY.MM.DD</p>
PAGE_MONTH_DAY = """
<div class="B01_Notice tabBox">
  <h2 class="tit_1"><a class="current" href="#">공지사항</a></h2>
  <div class="list_box on">
    <div class="top_list"><a href="/biohealth/na/ntt/selectNttInfo.do?nttSn=555538&amp;mi=5702">
      <dl><dt>혁신인재지원금 신청 안내</dt>
        <dd><p class="txt">신청기간 : ~2026.12.31.(목) 신청방법 : 온라인 폼</p>
          <p class="date"><span class="month">11</span><span class="day">23</span></p></dd></dl>
    </a></div>
    <ul>
      <li><a href="/biohealth/na/ntt/selectNttInfo.do?nttSn=555211&amp;mi=5702">
        [바이오헬스] 특별 강연 안내 (11/04 수 14시)<p>2026.11.03</p></a></li>
    </ul>
  </div>
</div>
"""

# ③ 맨 위 강조 글: <dd class="date">, 목록 글: p.tit + 이름 없는 <span>
PAGE_SPAN = """
<div class="tabBox">
  <h3><a href="#">공지사항</a></h3>
  <div class="list_box on">
    <div class="top_list"><a href="/djurise/na/ntt/selectNttInfo.do?nttSn=555633&amp;mi=7449">
      <dl><dt>현장실습기관 박람회 사전신청 안내</dt>
        <dd>신청기간 : 2026.11.24.(화) ~ 2026. 11. 30.(월)</dd>
        <dd class="date">2026-11-24</dd></dl></a></div>
    <ul><li><a href="/djurise/na/ntt/selectNttInfo.do?nttSn=555520&amp;mi=7449">
      <p class="tit">동계 현장실습학기제 참여학생 모집 안내</p><span>2026-11-19</span></a></li></ul>
  </div>
</div>
"""

# ④ 칸 이름이 '공지사항'이 아닌 사이트 (대학혁신: '사업단소식')
PAGE_OTHER_TAB = """
<div class="F01_Notice tabBox">
  <h2>Notice</h2>
  <h3 class="tit_1"><a class="currect" href="javascript:" title="사업단소식">사업단소식</a></h3>
  <div class="list_box on"><ul>
    <li><a href="/inno/na/ntt/selectNttInfo.do?nttSn=555560&amp;mi=1035&amp;bbsId=1004">
      <p class="tit">[2026년 11월] 프로그램 운영 일정</p><span class="date">2026-11-20</span>
      <p class="con">2026.12.31까지 신청</p></a></li>
  </ul></div>
</div>
"""


class ParseMainPageTest(unittest.TestCase):
    def parse(self, html, tab="공지사항", base=BASE, channel="SW중심대학사업단"):
        return ch.parse_main_page(html, base, channel, tab=tab, today=TODAY)

    def test_date_class_and_only_notice_tab(self):
        notices = self.parse(PAGE_DATE_CLASS)
        self.assertEqual([n["id"] for n in notices], ["homepage_sw_555675", "homepage_sw_555459"])
        first = notices[0]
        self.assertEqual(first["title"], "★[SW중심대학사업단] 공간 사용 신청서 양식★")
        self.assertEqual(first["posted_at"], "2026-11-26")
        self.assertEqual(
            first["url"],
            "https://www.dju.ac.kr/sw/na/ntt/selectNttInfo.do?nttSn=555675&mi=7358&bbsId=2758",
        )

    def test_schema_fields(self):
        notice = self.parse(PAGE_DATE_CLASS)[0]
        self.assertEqual(notice["source"], "auto")
        self.assertEqual(notice["channel"], "SW중심대학사업단")
        for key in ("is_notice", "apply_start", "apply_end", "deadline", "deadline_time", "target", "how_to_apply"):
            self.assertIsNone(notice[key], key)
        self.assertTrue(notice["collected_at"].endswith("+09:00"))

    def test_month_day_and_preview_date_ignored(self):
        top, item = self.parse(PAGE_MONTH_DAY)
        self.assertEqual(top["title"], "혁신인재지원금 신청 안내")
        self.assertEqual(top["posted_at"], "2026-11-23")  # 미리보기 속 2026.12.31이 아님
        self.assertEqual(item["title"], "[바이오헬스] 특별 강연 안내 (11/04 수 14시)")
        self.assertEqual(item["posted_at"], "2026-11-03")

    def test_month_day_uses_last_year_when_in_future(self):
        notices = ch.parse_main_page(PAGE_MONTH_DAY, BASE, "x", today=date(2026, 1, 5))
        self.assertEqual(notices[0]["posted_at"], "2025-11-23")

    def test_dd_date_and_plain_span(self):
        top, item = self.parse(PAGE_SPAN)
        self.assertEqual(top["posted_at"], "2026-11-24")
        self.assertEqual(item["title"], "동계 현장실습학기제 참여학생 모집 안내")
        self.assertEqual(item["posted_at"], "2026-11-19")

    def test_other_tab_name(self):
        notices = self.parse(PAGE_OTHER_TAB, tab="사업단소식", base="https://www.dju.ac.kr/inno/main.do")
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["id"], "homepage_inno_555560")
        self.assertEqual(notices[0]["posted_at"], "2026-11-20")  # .con 속 날짜가 아님

    def test_missing_tab_raises(self):
        with self.assertRaises(ValueError):
            self.parse(PAGE_OTHER_TAB)  # '공지사항' 칸이 없는 페이지

    def test_list_and_more_links_not_collected(self):
        urls = [n["url"] for n in self.parse(PAGE_DATE_CLASS)]
        self.assertFalse(any("selectNttList" in u for u in urls))


# ---------------------------------------------------------------- collect (가짜 session)


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text, self.status_code, self.encoding = text, status_code, "utf-8"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """요청한 주소를 기록하고, 정해 둔 응답을 돌려준다."""

    def __init__(self, pages):
        self.pages, self.requested, self.headers = pages, [], []

    def get(self, url, headers=None, timeout=None):
        self.requested.append(url)
        self.headers.append(headers or {})
        if url not in self.pages:
            return FakeResponse("", 404)
        return FakeResponse(self.pages[url])


class CollectTest(unittest.TestCase):
    def setUp(self):
        ch._robots_cache.clear()
        self.session = FakeSession({
            "https://www.dju.ac.kr/robots.txt": DJU_ROBOTS,
            "https://www.dju.ac.kr/sw/main.do": PAGE_DATE_CLASS,
            "https://www.dju.ac.kr/inno/main.do": PAGE_OTHER_TAB,
        })

    def test_collects_main_page_only(self):
        channel = {"name": "SW중심대학사업단", "url": "https://www.dju.ac.kr/sw/main.do"}
        notices = ch.collect(channel, session=self.session, today=TODAY)
        self.assertEqual(len(notices), 2)
        self.assertEqual(
            self.session.requested,
            ["https://www.dju.ac.kr/robots.txt", "https://www.dju.ac.kr/sw/main.do"],
        )
        # 공지 목록·본문(/*/na/ntt/)은 요청하지 않는다
        self.assertFalse(any("/na/ntt/" in u for u in self.session.requested))
        self.assertIn("MAGAMI", self.session.headers[1]["User-Agent"])
        self.assertIn("github.com/DJU-Chronos/MAGAMI", self.session.headers[1]["User-Agent"])

    def test_tab_from_channel_and_robots_cached(self):
        ch.collect({"name": "SW", "url": "https://www.dju.ac.kr/sw/main.do"}, session=self.session, today=TODAY)
        notices = ch.collect(
            {"name": "대학혁신지원사업", "url": "https://www.dju.ac.kr/inno/main.do", "tab": "사업단소식"},
            session=self.session, today=TODAY,
        )
        self.assertEqual(notices[0]["channel"], "대학혁신지원사업")
        self.assertEqual(self.session.requested.count("https://www.dju.ac.kr/robots.txt"), 1)

    def test_blocked_url_raises_without_request(self):
        channel = {"name": "게시판", "url": "https://www.dju.ac.kr/sw/na/ntt/selectNttList.do?bbsId=2758"}
        with self.assertRaises(PermissionError):
            ch.collect(channel, session=self.session, today=TODAY)
        self.assertEqual(self.session.requested, ["https://www.dju.ac.kr/robots.txt"])

    def test_no_robots_file_means_allowed(self):
        session = FakeSession({"https://example.ac.kr/main.do": PAGE_DATE_CLASS})
        notices = ch.collect({"name": "예시", "url": "https://example.ac.kr/main.do"}, session=session, today=TODAY)
        self.assertEqual(len(notices), 2)

    def test_load_channels_filters_enabled_and_allowed(self):
        import tempfile

        text = "\n".join([
            "homepages:",
            "  - {name: A, url: 'https://a/main.do', robots_allowed: true, enabled: true}",
            "  - {name: B, url: 'https://b/main.do', robots_allowed: true, enabled: false}",
            "  - {name: C, url: 'https://c/main.do', robots_allowed: false, enabled: true}",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.yaml"
            path.write_text(text, encoding="utf-8")
            self.assertEqual([c["name"] for c in ch.load_channels(path)], ["A"])


if __name__ == "__main__":
    unittest.main()
