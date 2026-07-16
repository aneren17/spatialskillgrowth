"""为已有 SpatialSkillGrowth run 补生成对话式 Markdown 轨迹。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nodes.mem.spatialskillgrowth.conversation_trace import (
    write_conversation_trace,
)


def render_run(run_root: Path) -> int:
    trajectory_root = run_root / "trajectories"
    rendered = 0
    for summary_path in sorted(trajectory_root.glob("*/summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        write_conversation_trace(
            trajectory_root,
            summary_path.parent.name,
            summary,
        )
        rendered += 1
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    args = parser.parse_args()
    count = render_run(args.run_root)
    print(f"已生成 {count} 份对话式轨迹。")


if __name__ == "__main__":
    main()
