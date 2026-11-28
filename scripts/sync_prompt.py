"""공통 추출 프롬프트를 크롬 확장 폴더로 복사한다.

크롬 확장은 extension/ 폴더 밖의 파일을 읽을 수 없어서 prompts/extract_notice.md를
extension/prompt.md로 복사해 둔다. 프롬프트를 고친 뒤에는 꼭 실행한다.

    python scripts/sync_prompt.py          # 복사
    python scripts/sync_prompt.py --check  # 두 파일이 같은지만 확인 (다르면 실패)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "prompts" / "extract_notice.md"
TARGET = ROOT / "extension" / "prompt.md"


def main(argv: list[str]) -> int:
    source = SOURCE.read_bytes()
    if "--check" in argv:
        if TARGET.exists() and TARGET.read_bytes() == source:
            print("extension/prompt.md가 최신입니다.")
            return 0
        print("extension/prompt.md가 prompts/extract_notice.md와 다릅니다. "
              "python scripts/sync_prompt.py 를 실행하세요.")
        return 1
    TARGET.write_bytes(source)
    print(f"복사했습니다: {SOURCE.relative_to(ROOT)} → {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
