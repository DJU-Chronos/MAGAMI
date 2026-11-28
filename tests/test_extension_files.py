"""크롬 확장 파일 점검: 프롬프트가 공통 프롬프트와 같은지, 권한이 약속한 범위인지."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtensionFilesTest(unittest.TestCase):
    def test_prompt_is_synced(self):
        source = (ROOT / "prompts" / "extract_notice.md").read_bytes()
        target = (ROOT / "extension" / "prompt.md").read_bytes()
        self.assertEqual(source, target, "python scripts/sync_prompt.py 를 실행하세요.")

    def test_permissions_are_minimal(self):
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        # 버튼을 누른 탭에만 접근: 모든 사이트 권한이나 자동 콘텐츠 스크립트를 쓰지 않는다
        self.assertEqual(sorted(manifest["permissions"]), ["activeTab", "scripting", "storage"])
        self.assertEqual(manifest["host_permissions"], ["https://generativelanguage.googleapis.com/*"])
        self.assertNotIn("content_scripts", manifest)
        self.assertNotIn("tabs", manifest["permissions"])


if __name__ == "__main__":
    unittest.main()
