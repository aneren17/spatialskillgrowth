"""校验并部署人工编写的 SpatialSkillGrowth Python Skill。
python -m scripts.deploy_spatialskillgrowth_skill \
    --skill-dir skills/spatialskillgrowth/banner \
    --script skills/spatialskillgrowth/banner/scripts/banner-crop-example.py

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nodes.mem.spatialskillgrowth.skills.human_skill_deployment import (
    deploy_human_skill,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖同 ID 但契约或脚本内容不同的现有人工 Workflow。",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = deploy_human_skill(
            args.skill_dir,
            args.script,
            force=args.force,
        )
    except Exception as exc:
        result = {
            "deployed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("deployed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
