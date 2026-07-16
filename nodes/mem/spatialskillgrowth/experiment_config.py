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
    OMNI3D_PROBLEM_CLASSES,
    class_metadata_for,
    normalize_benchmark,
    problem_classes_for,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULT_ROOT = "benchmark_result/spatialskillgrowth_omni3d"
DEFAULT_SKILL_WHITEBOARD_ROOT = PROJECT_ROOT / "skills" / "spatialskillgrowth_whiteboard"
SKILL_WHITEBOARD_FILE = "WHITEBOARD.json"
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
        benchmark: str = "omni3d",
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
        """从只读白板初始化新 run；恢复运行时绝不覆盖已有技能。"""
        if (
            self.benchmark != "omni3d"
            or tuple(self.problem_classes) != tuple(OMNI3D_PROBLEM_CLASSES)
        ):
            self._initialize_dynamic_skill_workspace()
            return
        whiteboard_path = DEFAULT_SKILL_WHITEBOARD_ROOT / SKILL_WHITEBOARD_FILE
        if not whiteboard_path.is_file():
            raise FileNotFoundError(f"Skill whiteboard does not exist: {whiteboard_path}")
        whiteboard = json.loads(whiteboard_path.read_text(encoding="utf-8"))
        problem_classes = _whiteboard_problem_classes(whiteboard)
        self.skill_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(whiteboard_path, self.skill_root / SKILL_WHITEBOARD_FILE)
        for item in problem_classes:
            problem_class = item["name"]
            source = DEFAULT_SKILL_WHITEBOARD_ROOT / problem_class
            required = (
                source / "SKILL.md",
                source / "skill.json",
                source / "scripts",
                source / "workflows",
            )
            if not all(path.exists() for path in required):
                raise ValueError(f"Incomplete skill whiteboard entry: {source}")
        for root in (
            self.active_skill_root,
            self.provisional_skill_root,
            self.archive_skill_root,
        ):
            shutil.copytree(
                DEFAULT_SKILL_WHITEBOARD_ROOT,
                root,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(SKILL_WHITEBOARD_FILE),
            )

    def _initialize_dynamic_skill_workspace(self) -> None:
        problem_classes = []
        for name in self.problem_classes:
            metadata = self.class_metadata.get(name, {})
            problem_classes.append({
                "name": name,
                "title": str(metadata.get("title") or name.replace("_", " ").title()),
                "description": str(
                    metadata.get("description")
                    or f"Reusable validated workflows for {name}."
                ),
            })
        if not problem_classes:
            raise ValueError(f"No problem classes configured for benchmark: {self.benchmark}")
        whiteboard = {
            "benchmark": self.benchmark,
            "description": "Run-local dynamic standard-skill whiteboard.",
            "problem_classes": problem_classes,
        }
        _write_json(self.skill_root / SKILL_WHITEBOARD_FILE, whiteboard)
        for status, root in (
            ("active", self.active_skill_root),
            ("provisional", self.provisional_skill_root),
            ("archive", self.archive_skill_root),
        ):
            skills = []
            for item in problem_classes:
                metadata = _write_blank_skill(root, item, status)
                skills.append(metadata)
            _write_json(root / "SKILLS.json", {"skills": skills})


def _write_json(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _whiteboard_problem_classes(whiteboard: Dict) -> List[Dict[str, str]]:
    values = whiteboard.get("problem_classes")
    if not isinstance(values, list) or not values:
        raise ValueError("Skill whiteboard must define non-empty problem_classes")
    output = []
    seen = set()
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("Each whiteboard problem class must be an object")
        name = str(value.get("name") or "")
        if _safe_component(name) != name or name in seen:
            raise ValueError(f"Invalid or duplicate whiteboard problem class: {name!r}")
        seen.add(name)
        output.append({
            "name": name,
            "title": str(value.get("title") or ""),
            "description": str(value.get("description") or ""),
        })
    return output


def _write_blank_skill(root: Path, item: Dict[str, str], status: str) -> Dict:
    name = item["name"]
    title = item["title"]
    description = item["description"]
    directory = root / name
    (directory / "scripts").mkdir(parents=True, exist_ok=True)
    (directory / "workflows").mkdir(parents=True, exist_ok=True)
    (directory / "scripts" / ".gitkeep").touch()
    (directory / "workflows" / ".gitkeep").touch()
    (directory / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## Purpose\n\n"
        f"{description}\n\n"
        "## Resources\n\n"
        "- `workflows/*.json` contains executable workflow definitions.\n"
        "- `scripts/*.py` contains generated Python functions whose parameters expose runtime slots.\n\n"
        "## Validated Workflows\n\n"
        "No workflow has passed validation in this run.\n",
        encoding="utf-8",
    )
    metadata = {
        "name": name,
        "title": title,
        "problem_class": name,
        "description": description,
        "status": status,
        "workflow_count": 0,
        "workflows": [],
    }
    _write_json(directory / "skill.json", metadata)
    return metadata


def _safe_component(value: str) -> str:
    component = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("._")
    if not component:
        raise ValueError("Experiment and run identifiers cannot be empty")
    return component


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
