"""重建不含历史工作流的 SpatialSkillGrowth 标准 skill 白板。"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict

from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_BENCHMARK,
    ANOMALY_CLASS_METADATA,
    ANOMALY_EVENT_TYPES,
)
from nodes.mem.spatialskillgrowth.skill_layout import (
    skill_metadata_path,
    standard_skill_name,
    workflow_reference_directory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "skills" / "spatialskillgrowth_whiteboard"
WHITEBOARD_README = """# SpatialSkillGrowth 标准模板

本目录由 `python -m scripts.build_spatialskillgrowth_whiteboard --force` 自动重建，只用于定义 55 个异常
事件类别的标准 Skill 结构、元数据和空工作流目录。请勿在这里编写或保存人工脚本。

人工维护位置是 `skills/spatialskillgrowth/`。实习生应在那里修改 `SKILL.md` 和 `scripts/*.py`，再运行
项目提供的验证器生成 `references/workflows/*.json`。
"""


def build_whiteboard(output: Path, force: bool = False) -> None:
    if output.exists():
        if not force:
            raise FileExistsError(f"Whiteboard already exists: {output}. Use --force to rebuild it.")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    skills = []
    problem_classes = []
    for problem_class in ANOMALY_EVENT_TYPES:
        metadata = dict(ANOMALY_CLASS_METADATA[problem_class])
        skill_name = standard_skill_name(problem_class)
        skill_metadata = _skill_metadata(problem_class, skill_name, metadata)
        skills.append(skill_metadata)
        problem_classes.append({
            "name": problem_class,
            "skill_name": skill_name,
            "title": metadata["title"],
            "description": metadata["description"],
            "aliases": metadata["aliases"],
            "display_names": metadata["display_names"],
        })
        directory = output / skill_name
        (directory / "scripts").mkdir(parents=True)
        workflow_reference_directory(directory).mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            _skill_markdown(problem_class, metadata),
            encoding="utf-8",
        )
        _write_json(skill_metadata_path(directory), skill_metadata)
        (directory / "scripts" / ".gitkeep").touch()
        (workflow_reference_directory(directory) / ".gitkeep").touch()
    _write_json(output / "SKILLS.json", {"skills": skills})
    _write_json(output / "WHITEBOARD.json", {
        "benchmark": ANOMALY_BENCHMARK,
        "description": "每个 SpatialSkillGrowth 异常检测运行使用的空白标准 Skill 工作区。",
        "problem_classes": problem_classes,
    })
    (output / "README.md").write_text(WHITEBOARD_README, encoding="utf-8")


def _skill_metadata(
    problem_class: str,
    skill_name: str,
    metadata: Dict[str, Any],
) -> Dict:
    return {
        "name": skill_name,
        "title": metadata["title"],
        "problem_class": problem_class,
        "event_type": problem_class,
        "description": metadata["description"],
        "aliases": metadata["aliases"],
        "display_names": metadata["display_names"],
        "primary_tool": metadata["primary_tool"],
        "answer_type": metadata["answer_type"],
        "required_slots": metadata["required_slots"],
        "tool_template": metadata["tool_template"],
        "evidence_requirements": metadata["evidence_requirements"],
        "workflow_count": 0,
        "workflows": [],
    }


def _skill_markdown(problem_class: str, metadata: Dict[str, Any]) -> str:
    description = metadata["description"]
    source_titles = {
        "dashboard": "大屏端",
        "rag": "RAG 检索/检测端",
        "stream": "实时视频流检测页",
    }
    display_name_rows = "\n".join(
        f"| {source_titles.get(source, source)} | {label} |"
        for source, label in metadata["display_names"].items()
    )
    evidence_rows = "\n".join(
        f"- {requirement}" for requirement in metadata["evidence_requirements"]
    )
    tool_template = json.dumps(
        metadata["tool_template"], ensure_ascii=False, indent=2
    )
    return (
        "---\n"
        f"name: {standard_skill_name(problem_class)}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {metadata['title']}\n\n"
        "## 用途\n\n"
        f"{description}\n\n"
        "## 事件接口\n\n"
        f"- 精确 `event_type`：`{problem_class}`\n"
        f"- 主检测工具：`{metadata['primary_tool']}`\n"
        f"- 答案类型：`{metadata['answer_type']}`，输出“是”或“否”\n"
        "- 结构化结果：必须包含 `is_anomaly` 和 `threshold`\n\n"
        "## 各端显示名称\n\n"
        "| 来源 | 中文显示名称 |\n"
        "|---|---|\n"
        f"{display_name_rows}\n\n"
        "## 工具调用模板\n\n"
        "```json\n"
        f"{tool_template}\n"
        "```\n\n"
        "## 证据要求\n\n"
        f"{evidence_rows}\n\n"
        "## 资源\n\n"
        "- 本 whiteboard 的 `scripts/` 只是空模板，不在这里编写人工脚本。\n"
        "- `references/skill.json` 保存机器可读的 Skill 索引。\n"
        "- 本 whiteboard 的 `references/workflows/` 保持为空。\n"
        "- 人工工作请复制到 `skills/spatialskillgrowth/` 并阅读项目级编写说明。\n\n"
        "## 已验证工作流\n\n"
        "当前运行尚无通过验证的工作流。\n"
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
