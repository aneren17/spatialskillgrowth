"""评测 SpatialSkillGrowth 的 JSON 推理产物，无需 qa_cache 数据库。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nodes.mem.spatialskillgrowth.omni3d_eval_adapter import (
    evaluate_run,
    print_summary,
)


DEFAULT_ANNOTATIONS = "benchmark/Omni-3d/annotations.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--annotations", default=DEFAULT_ANNOTATIONS)
    parser.add_argument(
        "--predictions",
        default="",
        help="Optional explicit omni3d_predictions.json; defaults to the run result.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = evaluate_run(
        Path(args.run_dir),
        Path(args.annotations),
        Path(args.predictions) if args.predictions else None,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
