"""collect_homepage.py 단위 테스트 (인터넷 없이 실행된다).

실행: python -m unittest discover -s tests
"""

import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
