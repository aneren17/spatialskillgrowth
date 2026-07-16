"""SpatialSkillGrowth 的核心 JSON 数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Type, TypeVar


T = TypeVar("T")


class SerializableRecord:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls: Type[T], value: Dict[str, Any]) -> T:
        return cls(**value)


class WorkflowStatus(str, Enum):
    ACTIVE = "active"
    PROVISIONAL = "provisional"
    ARCHIVE = "archive"


class MutationMode(str, Enum):
    SUCCESS_ENHANCEMENT = "success_enhancement"
    FAILURE_REPAIR = "failure_repair"
    EXTRACTED = "extracted"


@dataclass
class TaskRecord(SerializableRecord):
    task_id: str
    question: str
    groundtruth: str
    image_paths: List[str] = field(default_factory=list)
    capability: str = ""
    answer_type: str = ""
    media_type: str = ""
    sampled_frame_paths: List[str] = field(default_factory=list)
    media_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def media_path(self) -> str:
        return self.image_paths[0] if self.image_paths else ""

    @property
    def visual_paths(self) -> List[str]:
        return list(self.sampled_frame_paths or self.image_paths)


@dataclass
class ParamAtom(SerializableRecord):
    tool_name: str
    axis: str
    value: str
    kind: str
    description: str = ""
    args: Dict[str, Any] = field(default_factory=dict)

    @property
    def atom_id(self) -> str:
        return f"{self.tool_name}:{self.axis}:{self.value}"


@dataclass
class MutationSpec(SerializableRecord):
    mutation_id: str
    kind: str
    atom: ParamAtom
    operation: str
    description: str
    atoms: List[ParamAtom] = field(default_factory=list)
    score_parts: Dict[str, Dict[str, float]] = field(default_factory=dict)
    placements: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def selected_atoms(self) -> List[ParamAtom]:
        return self.atoms or [self.atom]

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "MutationSpec":
        data = dict(value)
        data["atom"] = ParamAtom.from_dict(data["atom"])
        data["atoms"] = [
            ParamAtom.from_dict(item) for item in data.get("atoms", [])
        ]
        return cls(**data)


@dataclass
class WorkflowStep(SerializableRecord):
    tool_name: str
    args: Dict[str, Any] = field(default_factory=dict)
    param_atoms: List[ParamAtom] = field(default_factory=list)
    purpose: str = ""
    step_id: str = ""
    depends_on: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "WorkflowStep":
        return cls(
            tool_name=str(value.get("tool_name") or ""),
            args=dict(value.get("args") or {}),
            param_atoms=[
                ParamAtom.from_dict(item)
                for item in value.get("param_atoms", [])
                if isinstance(item, dict)
            ],
            purpose=str(value.get("purpose") or ""),
            step_id=str(value.get("step_id") or ""),
            depends_on=list(value.get("depends_on") or []),
        )


@dataclass
class ApplicabilitySpec(SerializableRecord):
    """结构约束可硬过滤，自然语言语义只交给 LLM 判断。"""

    problem_class: str
    required_slots: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    answer_types: List[str] = field(default_factory=list)
    description: str = ""
    exclusions: str = ""
    capability_boundary: str = ""

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "ApplicabilitySpec":
        data = dict(value or {})
        return cls(
            problem_class=str(data.get("problem_class") or ""),
            required_slots=list(data.get("required_slots") or []),
            required_tools=list(data.get("required_tools") or []),
            answer_types=list(data.get("answer_types") or []),
            description=str(data.get("description") or ""),
            exclusions=str(data.get("exclusions") or ""),
            capability_boundary=str(data.get("capability_boundary") or ""),
        )


@dataclass
class WorkflowMetrics(SerializableRecord):
    trial_count: int = 0
    correct_count: int = 0
    evidence_accept_count: int = 0
    tool_failure_count: int = 0
    total_tool_calls: int = 0
    total_latency_ms: float = 0.0
    structural_coverage: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct_count / self.trial_count if self.trial_count else 0.0

    @property
    def evidence_rate(self) -> float:
        return self.evidence_accept_count / self.trial_count if self.trial_count else 0.0

    @property
    def average_cost(self) -> float:
        if not self.trial_count:
            return 0.0
        return (self.total_tool_calls + self.tool_failure_count) / self.trial_count

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "WorkflowMetrics":
        allowed = cls.__dataclass_fields__
        return cls(**{
            key: value[key] for key in allowed if key in (value or {})
        })


@dataclass
class WorkflowSpec(SerializableRecord):
    workflow_id: str
    name: str
    applicability: ApplicabilitySpec
    steps: List[WorkflowStep] = field(default_factory=list)
    status: str = WorkflowStatus.ACTIVE.value
    derived_from_workflow_id: str = ""
    mutation_mode: str = MutationMode.EXTRACTED.value
    mutation_direction: Dict[str, Any] = field(default_factory=dict)
    metrics: WorkflowMetrics = field(default_factory=WorkflowMetrics)
    source_task_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "WorkflowSpec":
        return cls(
            workflow_id=str(value.get("workflow_id") or ""),
            name=str(value.get("name") or ""),
            applicability=ApplicabilitySpec.from_dict(value.get("applicability") or {}),
            steps=[
                WorkflowStep.from_dict(item)
                for item in value.get("steps", [])
                if isinstance(item, dict)
            ],
            status=str(value.get("status") or WorkflowStatus.ACTIVE.value),
            derived_from_workflow_id=str(value.get("derived_from_workflow_id") or ""),
            mutation_mode=str(value.get("mutation_mode") or MutationMode.EXTRACTED.value),
            mutation_direction=dict(value.get("mutation_direction") or {}),
            metrics=WorkflowMetrics.from_dict(value.get("metrics") or {}),
            source_task_ids=list(value.get("source_task_ids") or []),
        )


@dataclass
class MutationDirection(SerializableRecord):
    mode: str
    objective: str
    preferred_atom_ids: List[str] = field(default_factory=list)
    avoid_atom_ids: List[str] = field(default_factory=list)
    tool_hints: Dict[str, str] = field(default_factory=dict)
    diagnosis: str = ""


@dataclass
class RetrievalDecision(SerializableRecord):
    strategy: str
    ranked_workflow_ids: List[str] = field(default_factory=list)
    rejected: bool = False
    reason: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceDecision(SerializableRecord):
    accepted: bool
    validator: str
    reason: str
    contract_checks: Dict[str, bool] = field(default_factory=dict)
