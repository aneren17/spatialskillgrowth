"""验证并可安装人工编写的 SpatialSkillGrowth Skill 脚本。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nodes.mem.spatialskillgrowth.human_skill_validation import (
    validate_human_skill,
)


DEFAULT_MEDIA = Path("test/banner.jpg")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--media", type=Path, default=DEFAULT_MEDIA)
    parser.add_argument("--event-type", required=True)
    parser.add_argument(
        "--real-tools",
        action="store_true",
        help="调用真实工具服务；默认使用确定性 mock 检查脚本逻辑。",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="验证通过后写入 scripts/ 和 references/workflows/。",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    report = validate_human_skill(
        args.skill_dir,
        args.script,
        args.media,
        args.event_type,
        real_tools=args.real_tools,
        install=args.install,
        force=args.force,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
