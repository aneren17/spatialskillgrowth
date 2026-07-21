"""异常检测探索和推理的运行配置与目录。"""

import json
import re
import shutil
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path

from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.core.anomaly_events import class_metadata_for_anomaly
from nodes.mem.spatialskillgrowth.skills.skill_layout import skill_directory
from nodes.mem.spatialskillgrowth.skills.skill_layout import skill_metadata_path
from nodes.mem.spatialskillgrowth.skills.skill_layout import standard_skill_name
from nodes.mem.spatialskillgrowth.skills.skill_layout import (
    workflow_reference_directory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESULT_ROOT = "benchmark_result/spatialskillgrowth_anomaly_detection"
DEFAULT_EDITABLE_SKILL_ROOT = PROJECT_ROOT / "skills" / "spatialskillgrowth"
RUN_SKILLSET_FILE = "SKILLSET.json"
DEFAULT_SEED = 3407


@dataclass
class ExperimentConfig:
    """只保留主算法和生命周期真正使用的参数。"""

    name: str = "full"
    seed: int = DEFAULT_SEED
    workflow_top_k: int = 3
    success_candidate_budget: int = 2
    failure_candidate_budget: int = 3
    active_cap_per_class: int = 12
    provisional_promotion_trials: int = 1
    provisional_validation_trials: int = 2
    provisional_validation_candidates_per_class: int = 4
    provisional_archive_trials: int = 5
    active_demotion_trials: int = 3
    promotion_accuracy: float = 0.5
    demotion_accuracy: float = 0.4
    archive_accuracy: float = 0.25
    use_react: bool = True
    success_enhancement: bool = True
    failure_repair: bool = True
    provisional_validation: bool = True
    one_shot_activation: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def build_experiment_config(seed=DEFAULT_SEED):
    return ExperimentConfig(seed=int(seed))


class ExperimentPaths:
    """一次异常检测运行的全部持久化目录。"""

    def __init__(
        self,
        run_id,
        result_root=DEFAULT_RESULT_ROOT,
        problem_classes=None,
        class_metadata=None,
    ):
        self.experiment = "full"
        self.run_id = _safe_component(run_id or _default_run_id())
        if problem_classes is None:
            problem_classes = ANOMALY_EVENT_TYPES
        self.problem_classes = tuple(problem_classes)
        if class_metadata is None:
            class_metadata = class_metadata_for_anomaly()
        self.class_metadata = class_metadata

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

    def ensure(self, config, mode, resume=False):
        manifest_path = self.root / "manifest.json"
        config_path = self.root / "config.json"
        is_new_run = not manifest_path.exists()
        if not is_new_run:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("run_id") != self.run_id:
                raise RuntimeError("运行目录的 run_id 不匹配：" + str(self.root))
            modes = manifest.get("modes") or []
            if mode in modes and not resume:
                raise FileExistsError(
                    "运行已存在，请使用 --resume 或新的 --run-id：" + str(self.root)
                )
            if config_path.exists():
                existing_config = json.loads(config_path.read_text(encoding="utf-8"))
                if existing_config != config.to_dict():
                    raise RuntimeError("运行配置不一致，请使用新的 --run-id。")
        else:
            self._initialize_skill_workspace()

        directories = [
            self.state_dir,
            self.active_skill_root,
            self.provisional_skill_root,
            self.archive_skill_root,
            self.trajectory_root,
            self.retrieval_root,
            self.results_root,
            self.metrics_root,
            self.export_root,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        previous_modes = []
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_modes = list(manifest.get("modes") or [])
        if mode not in previous_modes:
            previous_modes.append(mode)
        manifest = {
            "run_id": self.run_id,
            "problem_classes": list(self.problem_classes),
            "modes": previous_modes,
            "seed": config.seed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(manifest_path, manifest)
        _write_json(config_path, config.to_dict())

    def _initialize_skill_workspace(self):
        unknown_classes = set(self.problem_classes).difference(ANOMALY_EVENT_TYPES)
        if unknown_classes:
            values = ", ".join(sorted(unknown_classes))
            raise ValueError("不支持的异常事件类别：" + values)
        if not DEFAULT_EDITABLE_SKILL_ROOT.is_dir():
            raise FileNotFoundError(
                "人工 Skill 根目录不存在：" + str(DEFAULT_EDITABLE_SKILL_ROOT)
            )

        items = []
        for event_type in self.problem_classes:
            metadata = self.class_metadata[event_type]
            items.append({
                "name": event_type,
                "skill_name": standard_skill_name(event_type),
                "title": str(metadata.get("title") or event_type),
                "description": str(metadata.get("description") or ""),
            })

        self.skill_root.mkdir(parents=True, exist_ok=True)
        _write_json(self.skill_root / RUN_SKILLSET_FILE, {
            "source_root": str(DEFAULT_EDITABLE_SKILL_ROOT.resolve()),
            "problem_classes": items,
        })

        active_metadata = []
        for item in items:
            source = DEFAULT_EDITABLE_SKILL_ROOT / item["skill_name"]
            _validate_skill_source(source)
            target = self.active_skill_root / item["skill_name"]
            shutil.copytree(source, target, dirs_exist_ok=True)
            metadata_path = skill_metadata_path(target)
            active_metadata.append(json.loads(metadata_path.read_text(encoding="utf-8")))
        _write_json(self.active_skill_root / "SKILLS.json", {"skills": active_metadata})

        status_roots = [
            ("provisional", self.provisional_skill_root),
            ("archive", self.archive_skill_root),
        ]
        for status, root in status_roots:
            status_metadata = []
            for item in items:
                source = DEFAULT_EDITABLE_SKILL_ROOT / item["skill_name"]
                metadata = json.loads(
                    skill_metadata_path(source).read_text(encoding="utf-8")
                )
                skill_markdown = (source / "SKILL.md").read_text(encoding="utf-8")
                status_metadata.append(
                    _write_empty_skill(root, item, metadata, skill_markdown, status)
                )
            _write_json(root / "SKILLS.json", {"skills": status_metadata})


def _validate_skill_source(source):
    required_paths = [
        source / "SKILL.md",
        skill_metadata_path(source),
        source / "scripts",
        workflow_reference_directory(source),
    ]
    for path in required_paths:
        if not path.exists():
            raise ValueError("Skill 目录不完整：" + str(source))


def _write_empty_skill(root, item, metadata, skill_markdown, status):
    event_type = item["name"]
    directory = skill_directory(root, event_type)
    script_root = directory / "scripts"
    workflow_root = workflow_reference_directory(directory)
    script_root.mkdir(parents=True, exist_ok=True)
    workflow_root.mkdir(parents=True, exist_ok=True)
    (script_root / ".gitkeep").touch()
    (workflow_root / ".gitkeep").touch()
    (directory / "SKILL.md").write_text(skill_markdown, encoding="utf-8")

    output = dict(metadata)
    output["name"] = item["skill_name"]
    output["title"] = item["title"]
    output["problem_class"] = event_type
    output["description"] = item["description"]
    output["status"] = status
    output["workflow_count"] = 0
    output["workflows"] = []
    _write_json(skill_metadata_path(directory), output)
    return output


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2)
    path.write_text(content + "\n", encoding="utf-8")


def _safe_component(value):
    component = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or ""))
    component = component.strip("._")
    if not component:
        raise ValueError("run_id 不能为空。")
    return component


def _default_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
