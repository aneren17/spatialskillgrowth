"""重建不含历史工作流的 SpatialSkillGrowth 标准 skill 白板。"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict

from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    OMNI3D_CLASS_METADATA,
    OMNI3D_PROBLEM_CLASSES,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "skills" / "spatialskillgrowth_whiteboard"


def build_whiteboard(output: Path, force: bool = False) -> None:
    if output.exists():
        if not force:
            raise FileExistsError(f"Whiteboard already exists: {output}. Use --force to rebuild it.")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    skills = []
    problem_classes = []
    for problem_class in OMNI3D_PROBLEM_CLASSES:
        metadata = dict(OMNI3D_CLASS_METADATA[problem_class])
        skill_metadata = _skill_metadata(problem_class, metadata)
        skills.append(skill_metadata)
        problem_classes.append({
            "name": problem_class,
            "title": metadata["title"],
            "description": metadata["description"],
        })
        directory = output / problem_class
        (directory / "scripts").mkdir(parents=True)
        (directory / "workflows").mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            _skill_markdown(problem_class, metadata),
            encoding="utf-8",
        )
        _write_json(directory / "skill.json", skill_metadata)
        (directory / "scripts" / ".gitkeep").touch()
        (directory / "workflows" / ".gitkeep").touch()
    _write_json(output / "SKILLS.json", {"skills": skills})
    _write_json(output / "WHITEBOARD.json", {
        "benchmark": "omni3d",
        "description": (
            "Blank standard-skill workspace copied into every new "
            "SpatialSkillGrowth run."
        ),
        "problem_classes": problem_classes,
    })


def _skill_metadata(problem_class: str, metadata: Dict[str, str]) -> Dict:
    return {
        "name": problem_class,
        "title": metadata["title"],
        "problem_class": problem_class,
        "description": metadata["description"],
        "workflow_count": 0,
        "workflows": [],
    }


def _skill_markdown(problem_class: str, metadata: Dict[str, str]) -> str:
    description = metadata["description"]
    return (
        "---\n"
        f"name: {problem_class}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {metadata['title']}\n\n"
        "## Purpose\n\n"
        f"{description}\n\n"
        "## Resources\n\n"
        "- `workflows/*.json` contains executable workflow definitions.\n"
        "- `scripts/*.py` contains generated Python functions whose parameters expose runtime slots.\n\n"
        "## Validated Workflows\n\n"
        "No workflow has passed validation in this run.\n"
    )


def _write_json(path: Path, value: Dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build_whiteboard(args.output, args.force)
    print(f"Built SpatialSkillGrowth skill whiteboard: {args.output}")


if __name__ == "__main__":
    main()
