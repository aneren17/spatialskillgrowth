"""使用确定性 mock 验证人工编写的 SpatialSkillGrowth Skill 脚本。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nodes.mem.spatialskillgrowth.skills.human_skill_validation import (
    validate_human_skill,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    args = parser.parse_args()
    report = validate_human_skill(
        args.skill_dir,
        args.script,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
