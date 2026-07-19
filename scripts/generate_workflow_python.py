"""从 JSON 工作流生成或重建可读 Python Skill。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.runtime.workflow_executor import (
    WorkflowPythonExporter,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow_json")
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing Python script. Without this flag, manual edits are preserved.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    workflow_path = Path(args.workflow_json)
    workflow = WorkflowSpec.from_dict(
        json.loads(workflow_path.read_text(encoding="utf-8"))
    )
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else workflow_path.parents[1] / "scripts"
    )
    path = WorkflowPythonExporter(output_dir).export(workflow, force=args.force)
    print(path)


if __name__ == "__main__":
    main()
