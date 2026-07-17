"""论文实验预设及运行目录隔离。"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_BENCHMARK,
    ANOMALY_EVENT_TYPES,
    class_metadata_for,
    normalize_benchmark,
    problem_classes_for,
)
from nodes.mem.spatialskillgrowth.skill_layout import (
    skill_directory,
    skill_metadata_path,
    standard_skill_name,
    workflow_reference_directory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULT_ROOT = "benchmark_result/spatialskillgrowth_anomaly_detection"
DEFAULT_SKILL_WHITEBOARD_ROOT = PROJECT_ROOT / "skills" / "spatialskillgrowth_whiteboard"
DEFAULT_EDITABLE_SKILL_ROOT = PROJECT_ROOT / "skills" / "spatialskillgrowth"
RUN_SKILLSET_FILE = "SKILLSET.json"
DEFAULT_SEED = 3407
DEFAULT_TOP_K = 3
DEFAULT_ACTIVE_CAP = 12


@dataclass
class ExperimentConfig:
    name: str = "full"
    retriever: str = "multimodal_llm_flat"
    use_retrieval: bool = True
    use_react: bool = True
    exploration_use_react: bool = True
    success_enhancement: bool = True
    failure_repair: bool = True
    mutation_selector: str = "direction_ucb"
    evidence_validation: str = "hybrid"
    semantic_consolidation: bool = True
    workflow_top_k: int = DEFAULT_TOP_K
    success_candidate_budget: int = 2
    failure_candidate_budget: int = 3
    active_cap_per_class: int = DEFAULT_ACTIVE_CAP
    provisional_promotion_trials: int = 2
    one_shot_activation: bool = False
    provisional_validation: bool = True
    provisional_validation_trials: int = 2
    provisional_validation_candidates_per_class: int = 4
    provisional_archive_trials: int = 5
    active_demotion_trials: int = 3
    promotion_accuracy: float = 0.6
    demotion_accuracy: float = 0.4
    archive_accuracy: float = 0.25
    seed: int = DEFAULT_SEED
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


EXPERIMENT_PRESETS = {
    "full": {},
    "react_only": {"use_retrieval": False, "success_enhancement": False, "failure_repair": False},
    "retrieval_only": {"use_react": False, "success_enhancement": False, "failure_repair": False},
    "no_retrieval": {"use_retrieval": False},
    "no_success_enhancement": {"success_enhancement": False},
    "no_failure_repair": {"failure_repair": False},
    "no_ucb": {"mutation_selector": "direction_only"},
    "no_evidence_validation": {"evidence_validation": "none"},
    "no_semantic_consolidation": {"semantic_consolidation": False},
    "legacy_tree": {"retriever": "legacy_tree"},
    "history_only": {"retriever": "history_only"},
}


def build_experiment_config(name: str, seed: int = DEFAULT_SEED) -> ExperimentConfig:
    if name not in EXPERIMENT_PRESETS:
        choices = ", ".join(sorted(EXPERIMENT_PRESETS))
        raise ValueError(f"Unknown experiment '{name}'. Available: {choices}")
    values = dict(EXPERIMENT_PRESETS[name])
    values.update({"name": name, "seed": int(seed)})
    return ExperimentConfig(**values)


def result_root_for_benchmark(benchmark: str) -> str:
    normalized = normalize_benchmark(benchmark)
    return f"benchmark_result/spatialskillgrowth_{_safe_component(normalized)}"


class ExperimentPaths:
    """为一次探索/推理运行创建不可混用的产物目录。"""

    def __init__(
        self,
        experiment: str,
        run_id: str,
        result_root: str = DEFAULT_RESULT_ROOT,
        benchmark: str = ANOMALY_BENCHMARK,
        problem_classes: Optional[List[str]] = None,
        class_metadata: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self.experiment = _safe_component(experiment)
        self.run_id = _safe_component(run_id or _default_run_id())
        self.benchmark = normalize_benchmark(benchmark)
        self.problem_classes = tuple(dict.fromkeys(
            str(item).strip()
            for item in (problem_classes or problem_classes_for(self.benchmark))
            if str(item).strip()
        ))
        self.class_metadata = class_metadata or class_metadata_for(self.benchmark)
        self.root = Path(result_root) / self.experiment / self.run_id
        self.state_dir = self.root / "state"
        self.skill_root = self.root / "skills"
        self.active_skill_root = self.skill_root / "active"
        self.provisional_skill_root = self.skill_root / "provisional"
        self.archive_skill_root = self.skill_root / "archive"
        self.trajectory_root = self.root / "trajectories"
        self.retrieval_root = self.root / "retrieval_rankings"
        self.results_root = self.root / "results"
        self.metrics_root = self.root / "metrics"
        self.export_root = self.root / "exports" / "python"

    def ensure(self, config: ExperimentConfig, mode: str, resume: bool) -> None:
        manifest_path = self.root / "manifest.json"
        config_path = self.root / "config.json"
        is_new_run = not manifest_path.exists()
        if not is_new_run:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = {
                "experiment": config.name,
                "run_id": self.run_id,
                "benchmark": self.benchmark,
            }
            actual = {key: existing.get(key) for key in expected}
            if actual != expected:
                raise RuntimeError(f"Run directory belongs to another experiment: {self.root}")
            existing_modes = set(existing.get("modes") or [existing.get("mode")])
            if not resume and mode in existing_modes:
                raise FileExistsError(
                    f"Run already exists: {self.root}. Use --resume or a new --run-id."
                )
            if config_path.exists():
                existing_config = json.loads(config_path.read_text(encoding="utf-8"))
                if existing_config != config.to_dict():
                    raise RuntimeError(
                        f"Run config mismatch: {self.root}. Use a new --run-id."
                    )
        if is_new_run:
            self._initialize_skill_workspace()
        for path in (
            self.state_dir,
            self.active_skill_root,
            self.provisional_skill_root,
            self.archive_skill_root,
            self.trajectory_root,
            self.retrieval_root,
            self.results_root,
            self.metrics_root,
            self.export_root,
        ):
            path.mkdir(parents=True, exist_ok=True)
        previous_modes = []
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_modes = list(previous.get("modes") or [previous.get("mode")])
        modes = list(dict.fromkeys(item for item in previous_modes + [mode] if item))
        manifest = {
            "experiment": config.name,
            "run_id": self.run_id,
            "benchmark": self.benchmark,
            "problem_classes": list(self.problem_classes),
            "mode": mode,
            "modes": modes,
            "seed": config.seed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(manifest_path, manifest)
        _write_json(config_path, config.to_dict())

    def _initialize_skill_workspace(self) -> None:
        """从人工可编辑 Skill 根初始化异常 active；恢复运行时不覆盖。"""
        if self.benchmark != ANOMALY_BENCHMARK:
            self._initialize_dynamic_skill_workspace()
            return
        unknown_classes = set(self.problem_classes).difference(ANOMALY_EVENT_TYPES)
        if unknown_classes:
            raise ValueError(
                "Unknown anomaly problem classes: "
                + ", ".join(sorted(unknown_classes))
            )
        problem_classes = []
        for name in self.problem_classes:
            metadata = self.class_metadata.get(name, {})
            problem_classes.append({
                "name": name,
                "skill_name": standard_skill_name(name),
                "title": str(metadata.get("title") or name),
                "description": str(metadata.get("description") or ""),
            })
        item_by_name = {item["name"]: item for item in problem_classes}
        selected_items = [item_by_name[name] for name in self.problem_classes]
        if not DEFAULT_EDITABLE_SKILL_ROOT.is_dir():
            raise FileNotFoundError(
                "Editable Skill root does not exist: "
                f"{DEFAULT_EDITABLE_SKILL_ROOT}"
            )
        self.skill_root.mkdir(parents=True, exist_ok=True)
        _write_json(self.skill_root / RUN_SKILLSET_FILE, {
            "benchmark": self.benchmark,
            "description": "Run-local Skill set initialized from editable skills.",
            "source_root": str(DEFAULT_EDITABLE_SKILL_ROOT.resolve()),
            "problem_classes": selected_items,
        })
        active_skills = []
        for item in selected_items:
            problem_class = item["name"]
            source = DEFAULT_EDITABLE_SKILL_ROOT / item["skill_name"]
            required = (
                source / "SKILL.md",
                skill_metadata_path(source),
                source / "scripts",
                workflow_reference_directory(source),
            )
            if not all(path.exists() for path in required):
                raise ValueError(f"Incomplete skill whiteboard entry: {source}")
            target = self.active_skill_root / item["skill_name"]
            shutil.copytree(source, target, dirs_exist_ok=True)
            active_skills.append(json.loads(
                skill_metadata_path(target).read_text(encoding="utf-8")
            ))
        _write_json(
            self.active_skill_root / "SKILLS.json",
            {"skills": active_skills},
        )
        for status, root in (
            ("provisional", self.provisional_skill_root),
            ("archive", self.archive_skill_root),
        ):
            skills = []
            for item in selected_items:
                source = DEFAULT_EDITABLE_SKILL_ROOT / item["skill_name"]
                blank_item = dict(item)
                blank_item["metadata"] = json.loads(
                    skill_metadata_path(source).read_text(encoding="utf-8")
                )
                blank_item["skill_markdown"] = (
                    source / "SKILL.md"
                ).read_text(encoding="utf-8")
                metadata = _write_blank_skill(root, blank_item, status)
                skills.append(metadata)
            _write_json(root / "SKILLS.json", {"skills": skills})

    def _initialize_dynamic_skill_workspace(self) -> None:
        problem_classes = []
        for name in self.problem_classes:
            metadata = self.class_metadata.get(name, {})
            problem_classes.append({
                "name": name,
                "skill_name": standard_skill_name(name),
                "title": str(metadata.get("title") or name.replace("_", " ").title()),
                "description": str(
                    metadata.get("description")
                    or f"Reusable validated workflows for {name}."
                ),
            })
        if not problem_classes:
            raise ValueError(f"No problem classes configured for benchmark: {self.benchmark}")
        skillset = {
            "benchmark": self.benchmark,
            "description": "Run-local dynamic standard Skill set.",
            "problem_classes": problem_classes,
        }
        _write_json(self.skill_root / RUN_SKILLSET_FILE, skillset)
        for status, root in (
            ("active", self.active_skill_root),
            ("provisional", self.provisional_skill_root),
            ("archive", self.archive_skill_root),
        ):
            skills = []
            for item in problem_classes:
                blank_item = dict(item)
                blank_item["metadata"] = dict(
                    self.class_metadata.get(item["name"], {})
                )
                blank_item["metadata"].setdefault("event_type", item["name"])
                metadata = _write_blank_skill(root, blank_item, status)
                skills.append(metadata)
            _write_json(root / "SKILLS.json", {"skills": skills})


def _write_json(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_blank_skill(root: Path, item: Dict[str, str], status: str) -> Dict:
    name = item["name"]
    skill_name = str(item.get("skill_name") or standard_skill_name(name))
    title = item["title"]
    description = item["description"]
    directory = skill_directory(root, name)
    (directory / "scripts").mkdir(parents=True, exist_ok=True)
    workflow_reference_directory(directory).mkdir(parents=True, exist_ok=True)
    (directory / "scripts" / ".gitkeep").touch()
    (workflow_reference_directory(directory) / ".gitkeep").touch()
    skill_markdown = str(item.get("skill_markdown") or "")
    if not skill_markdown:
        skill_markdown = (
            "---\n"
            f"name: {skill_name}\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            "---\n\n"
            f"# {title}\n\n"
            "## 用途\n\n"
            f"{description}\n\n"
            "## 资源\n\n"
            "- `scripts/*.py` 保存人工或自动生成的实际执行脚本。\n"
            "- `references/skill.json` 保存机器可读索引。\n"
            "- `references/workflows/*.json` 保存可检索工作流契约。\n"
        )
    (directory / "SKILL.md").write_text(skill_markdown, encoding="utf-8")
    metadata = dict(item.get("metadata") or {})
    metadata.update({
        "name": skill_name,
        "title": title,
        "problem_class": name,
        "description": description,
        "status": status,
        "workflow_count": 0,
        "workflows": [],
    })
    _write_json(skill_metadata_path(directory), metadata)
    return metadata


def _safe_component(value: str) -> str:
    component = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("._")
    if not component:
        raise ValueError("Experiment and run identifiers cannot be empty")
    return component


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
