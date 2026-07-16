"""ParamType mutation generation and workflow-level coverage selection."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from typing import Dict, Iterable, List, Optional, Set, Tuple

from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_UCB_C
from nodes.mem.spatialskillgrowth.models import MutationSpec, ParamAtom, WorkflowSpec
from nodes.mem.spatialskillgrowth.tool_contracts import can_add_tool, compatible_producers


COMMON_MUTATIONS = (
    ParamAtom(
        "embeddingTool",
        "event_type",
        "runtime_event_type",
        "fixed",
        "使用当前异常事件类别对应的精确 event_type 进行检测。",
        args={"file_path": "$media", "event_type": "$slot.event_type"},
    ),
    ParamAtom("MLLM", "scope", "whole_image", "world_model", "分析完整图像。"),
    ParamAtom("MLLM", "scope", "local_regions", "world_model", "分析已定位的局部区域。"),
    ParamAtom("MLLM", "evidence_focus", "explicit_visual_cues", "world_model", "要求给出明确的视觉线索。"),
    ParamAtom("yoloTool", "threshold", "low", "numerical", "使用 0.3 的检测阈值。"),
    ParamAtom("yoloTool", "threshold", "medium", "numerical", "使用 0.5 的检测阈值。"),
    ParamAtom("sam3", "threshold", "low", "numerical", "以 0.3 阈值重试困难目标并获取掩码和边界框。"),
    ParamAtom("sam3", "threshold", "medium", "numerical", "以 0.5 阈值分割抽象目标并获取掩码和边界框。"),
    ParamAtom("sam3", "threshold", "high", "numerical", "以 0.7 阈值分割具体目标并获取掩码和边界框。"),
    ParamAtom("sam3", "evidence_role", "mask_and_box_geometry", "fixed", "把分割图和 xyxy 像素边界框作为互补证据。"),
    ParamAtom("groundingdino", "box_threshold", "low", "numerical", "使用 0.3 的开放词汇检测阈值。"),
    ParamAtom("groundingdino", "box_threshold", "medium", "numerical", "使用 0.5 的开放词汇检测阈值。"),
    ParamAtom("groundingdino", "evidence_role", "open_vocabulary_localization", "fixed", "定位闭集检测词表之外的运行时指定目标。"),
    ParamAtom("paddleOcrTool", "evidence_role", "text_reading", "fixed", "读取可见文字。"),
    ParamAtom("paddleHeadDetTool", "target", "head", "fixed", "检测可见的人头。"),
    ParamAtom("paddlePedriderDetTool", "target", "traffic_subject", "fixed", "检测行人、骑行者和车辆。"),
    ParamAtom("crop_detections", "operation", "insert_after_detection", "structural", "检查已检测区域。"),
    ParamAtom("picRelativeCut", "operation", "insert_relative_crop", "structural", "在裁剪图中保留目标的相对布局。"),
    ParamAtom("python_code_sandbox", "operation", "append_verification", "structural", "验证数值或几何计算结果。"),
)

CLASS_MUTATIONS: Dict[str, tuple[ParamAtom, ...]] = {
    "counting": (
        ParamAtom("MLLM", "reasoning_role", "counting", "world_model", "Count visible target instances."),
        ParamAtom("yoloTool", "evidence_role", "counting_evidence", "fixed", "Detect countable instances."),
    ),
    "spatial_relation": (
        ParamAtom("MLLM", "reasoning_role", "spatial_relation", "world_model", "Compare an object pair."),
        ParamAtom("sam3", "evidence_role", "localization", "fixed", "Localize target masks and bounding boxes."),
    ),
    "size": (
        ParamAtom("MLLM", "reasoning_role", "size_compare", "world_model", "Compare visible extent."),
        ParamAtom("python_code_sandbox", "operation", "bbox_area_compare", "structural", "Compare box areas."),
    ),
    "distance_depth": (
        ParamAtom("MLLM", "reasoning_role", "depth_order", "world_model", "Use occlusion and depth cues."),
        ParamAtom("picRelativeCut", "evidence_role", "layout_preservation", "structural", "Preserve relative layout."),
        ParamAtom("unidepth", "evidence_role", "metric_depth", "fixed", "Estimate metric depth for localized runtime targets."),
    ),
    "orientation": (
        ParamAtom("MLLM", "reasoning_role", "orientation_check", "world_model", "Inspect pose and facing cues."),
        ParamAtom("crop_detections", "evidence_role", "local_pose", "structural", "Inspect localized pose."),
    ),
}

# Omni3D 使用专用 problem class。这里声明的是结构化 ParamType 坐标，不通过
# question/applicability 文本关键词选择，因此可直接用于 mutation 消融。
OMNI3D_CLASS_MUTATIONS: Dict[str, tuple[ParamAtom, ...]] = {
    "metric_dimension_scaling": (
        ParamAtom("groundingdino", "evidence_role", "reference_target_boxes", "fixed", "Localize both metric reference and target objects."),
        ParamAtom("MLLM", "reasoning_role", "metric_dimension_scale", "world_model", "Transfer a known reference dimension to the target."),
        ParamAtom("python_code_sandbox", "operation", "metric_scale", "structural", "Compute the calibrated dimension ratio."),
    ),
    "metric_distance_scaling": (
        ParamAtom("groundingdino", "evidence_role", "depth_targets", "fixed", "Localize the reference and target objects for depth."),
        ParamAtom("unidepth", "evidence_role", "metric_depth", "fixed", "Estimate metric depth at localized targets."),
        ParamAtom("python_code_sandbox", "operation", "distance_scale", "structural", "Compute a calibrated distance."),
    ),
    "dimension_ratio": (
        ParamAtom("groundingdino", "evidence_role", "dimension_boxes", "fixed", "Localize objects for dimension comparison."),
        ParamAtom("python_code_sandbox", "operation", "dimension_ratio", "structural", "Compute the requested dimension ratio."),
    ),
    "volume_capacity": (
        ParamAtom("MLLM", "reasoning_role", "volume_estimation", "world_model", "Estimate three-dimensional extents for both objects."),
        ParamAtom("python_code_sandbox", "operation", "volume_ratio", "structural", "Compute a volume capacity ratio."),
    ),
    "linear_fit_stacking": (
        ParamAtom("groundingdino", "evidence_role", "fit_geometry", "fixed", "Localize repeated and target extents."),
        ParamAtom("python_code_sandbox", "operation", "linear_fit", "structural", "Compute repeated-object fit or stacking count."),
    ),
    "object_counting": (
        ParamAtom("groundingdino", "evidence_role", "open_counting", "fixed", "Localize open-vocabulary count targets."),
        ParamAtom("MLLM", "reasoning_role", "constrained_count", "world_model", "Apply the requested inclusion and exclusion constraints."),
    ),
    "count_arithmetic": (
        ParamAtom("groundingdino", "evidence_role", "multi_group_count", "fixed", "Localize every group used by the arithmetic."),
        ParamAtom("python_code_sandbox", "operation", "count_arithmetic", "structural", "Apply deterministic arithmetic to group counts."),
    ),
    "count_comparison": (
        ParamAtom("groundingdino", "evidence_role", "comparison_groups", "fixed", "Localize both groups before comparing counts."),
        ParamAtom("MLLM", "reasoning_role", "count_compare", "world_model", "Compare grounded group counts."),
    ),
    "depth_ordering": (
        ParamAtom("groundingdino", "evidence_role", "depth_targets", "fixed", "Localize targets for relative depth."),
        ParamAtom("unidepth", "evidence_role", "relative_depth", "fixed", "Estimate target depths for ordering."),
    ),
    "depth_filtered_counting": (
        ParamAtom("groundingdino", "evidence_role", "depth_filtered_targets", "fixed", "Localize count targets and the depth reference."),
        ParamAtom("unidepth", "evidence_role", "filtered_depth", "fixed", "Estimate depth for each localized target."),
        ParamAtom("python_code_sandbox", "operation", "depth_filter_count", "structural", "Filter target depths and count matches."),
    ),
    "compass_direction": (
        ParamAtom("MLLM", "reasoning_role", "egocentric_compass", "world_model", "Transform the stated facing frame into a compass direction."),
    ),
    "occlusion_visibility": (
        ParamAtom("sam3", "evidence_role", "occlusion_masks_and_boxes", "fixed", "Collect masks and xyxy boxes for the occluder and target."),
        ParamAtom("MLLM", "reasoning_role", "visibility_transition", "world_model", "Predict visibility after the stated placement."),
    ),
    "physical_interaction": (
        ParamAtom("MLLM", "reasoning_role", "physical_dynamics", "world_model", "Reason about support, collision, falling, and motion."),
    ),
    "size_fit_comparison": (
        ParamAtom("groundingdino", "evidence_role", "fit_extents", "fixed", "Localize both objects for extent comparison."),
        ParamAtom("MLLM", "reasoning_role", "qualitative_fit", "world_model", "Judge three-dimensional size and fit."),
    ),
    "relative_3d_position": (
        ParamAtom("groundingdino", "evidence_role", "relation_targets", "fixed", "Localize both relation targets."),
        ParamAtom("MLLM", "reasoning_role", "relative_3d_relation", "world_model", "Resolve the requested three-dimensional relation."),
    ),
    "visual_attribute_recognition": (
        ParamAtom("crop_detections", "evidence_role", "attribute_crop", "structural", "Inspect a localized attribute region."),
        ParamAtom("MLLM", "reasoning_role", "visual_attribute", "world_model", "Recognize the requested visual attribute."),
    ),
}
CLASS_MUTATIONS.update(OMNI3D_CLASS_MUTATIONS)


class ParamSpace:
    def __init__(
        self,
        extra_atoms: Optional[Dict[str, Iterable[ParamAtom]]] = None,
    ):
        self.replace_extra_atoms(extra_atoms or {})

    def replace_extra_atoms(
        self,
        extra_atoms: Dict[str, Iterable[ParamAtom]],
    ) -> None:
        self.extra_atoms = {
            str(problem_class): list(atoms)
            for problem_class, atoms in extra_atoms.items()
        }

    def atoms_for(self, problem_class: str) -> List[ParamAtom]:
        atoms = (
            list(COMMON_MUTATIONS)
            + list(CLASS_MUTATIONS.get(problem_class, ()))
            + list(self.extra_atoms.get("*", ()))
            + list(self.extra_atoms.get(problem_class, ()))
        )
        unique = {atom.atom_id: atom for atom in atoms}
        return [unique[key] for key in sorted(unique)]

    def candidate_portfolios(
        self,
        problem_class: str,
        atom_stats: Dict[str, Dict[str, int]],
        workflow_tools: Iterable[str] = (),
        allowed_tool_names: Optional[Iterable[str]] = None,
        preferred_atom_ids: Iterable[str] = (),
        avoid_atom_ids: Iterable[str] = (),
        placements: Optional[Dict[str, Dict]] = None,
        atoms_per_portfolio: int = 3,
    ) -> List[MutationSpec]:
        parent_tools = set(workflow_tools)
        available_tools = (
            set(allowed_tool_names)
            if allowed_tool_names is not None
            else {atom.tool_name for atom in self.atoms_for(problem_class)}
        )
        avoided = set(avoid_atom_ids)
        atoms = [
            atom for atom in self.atoms_for(problem_class)
            if atom.tool_name in available_tools and atom.atom_id not in avoided
        ]
        preferred = set(preferred_atom_ids)
        preferred_atoms = [atom for atom in atoms if atom.atom_id in preferred]
        pool = list(preferred_atoms or atoms)
        if preferred_atoms:
            prerequisite_tools = set()
            for atom in preferred_atoms:
                prerequisite_tools.update(compatible_producers(atom.tool_name))
            pool.extend(
                atom for atom in atoms
                if atom.tool_name in prerequisite_tools and atom not in pool
            )
        total_trials = sum(
            max(0, int(item.get("trial_count", 0) or 0))
            for item in atom_stats.values()
        )
        candidates = []
        max_size = min(max(1, atoms_per_portfolio), len(pool))
        for size in range(1, max_size + 1):
            for selected in itertools.combinations(pool, size):
                axes = {(atom.tool_name, atom.axis) for atom in selected}
                if len(axes) != len(selected):
                    continue
                final_tools = parent_tools.union(atom.tool_name for atom in selected)
                if not all(can_add_tool(atom.tool_name, final_tools) for atom in selected):
                    continue
                candidates.append(self._mutation_spec(
                    selected,
                    atom_stats,
                    total_trials,
                    placements or {},
                ))
        return candidates

    def select_workflow_mutations(
        self,
        candidates: List[Tuple[MutationSpec, WorkflowSpec]],
        parent_workflow: WorkflowSpec,
        active_workflows: Iterable[WorkflowSpec],
        atom_stats: Dict[str, Dict[str, int]],
        count: int = 3,
        allow_zero_gain: bool = False,
    ) -> List[Tuple[MutationSpec, WorkflowSpec]]:
        active = list(active_workflows)
        best_coverage = self._best_coverage(active)
        parent_features = self.workflow_features(parent_workflow)
        ranked_candidates = []
        seen_workflows = set()
        for mutation, workflow in candidates:
            signature = json.dumps(
                [step.to_dict() for step in workflow.steps],
                sort_keys=True,
                ensure_ascii=True,
            )
            if signature in seen_workflows:
                continue
            seen_workflows.add(signature)
            features = self.workflow_features(workflow).difference(parent_features)
            if not features:
                continue
            quality = self._mutation_quality(mutation, atom_stats)
            gain = self._marginal_gain(features, quality, best_coverage)
            ranked_candidates.append((mutation, workflow, features, quality, gain))

        selected = []
        for _ in range(max(1, count)):
            if not ranked_candidates:
                break
            ranked_candidates.sort(
                key=lambda item: (-item[4], item[0].mutation_id)
            )
            if ranked_candidates[0][4] <= 0 and not allow_zero_gain:
                break
            mutation, workflow, features, quality, gain = ranked_candidates.pop(0)
            mutation.score_parts["workflow"] = {
                "quality": round(quality, 6),
                "coverage_gain": round(gain, 6),
                "feature_count": float(len(features)),
            }
            selected.append((mutation, workflow))
            for feature in features:
                best_coverage[feature] = max(best_coverage.get(feature, 0.0), quality)
            ranked_candidates = [
                (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    self._marginal_gain(item[2], item[3], best_coverage),
                )
                for item in ranked_candidates
            ]
        return selected

    def workflow_marginal_gain(
        self,
        workflow: WorkflowSpec,
        active_workflows: Iterable[WorkflowSpec],
    ) -> float:
        active = [
            item for item in active_workflows
            if item.workflow_id != workflow.workflow_id
        ]
        best_coverage = self._best_coverage(active)
        quality = self._workflow_quality(
            workflow,
            sum(max(0, item.metrics.trial_count) for item in active),
        )
        return self._marginal_gain(
            self.workflow_features(workflow), quality, best_coverage
        )

    def merge_candidates(
        self,
        workflow: WorkflowSpec,
        active_workflows: Iterable[WorkflowSpec],
        limit: int = 5,
    ) -> List[WorkflowSpec]:
        features = self.workflow_features(workflow)
        ranked = []
        for existing in active_workflows:
            if existing.workflow_id == workflow.workflow_id:
                continue
            existing_features = self.workflow_features(existing)
            union = features.union(existing_features)
            overlap = len(features.intersection(existing_features)) / max(1, len(union))
            if overlap > 0:
                ranked.append((
                    overlap,
                    existing.metrics.correct_count,
                    existing.workflow_id,
                    existing,
                ))
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [item[3] for item in ranked[:max(1, limit)]]

    @staticmethod
    def workflow_features(workflow: WorkflowSpec) -> Set[str]:
        features = set()
        step_tools = {step.step_id: step.tool_name for step in workflow.steps}
        for step in workflow.steps:
            features.add(f"tool:{step.tool_name}")
            for atom in step.param_atoms:
                features.update({
                    f"axis:{atom.tool_name}:{atom.axis}",
                    f"atom:{atom.atom_id}",
                })
            for dependency in step.depends_on:
                producer = step_tools.get(dependency)
                if producer:
                    features.add(f"edge:{producer}->{step.tool_name}")
        return features

    @staticmethod
    def _mutation_spec(
        atoms: Tuple[ParamAtom, ...],
        atom_stats: Dict[str, Dict[str, int]],
        total_trials: int,
        placements: Dict[str, Dict],
    ) -> MutationSpec:
        selected = list(atoms)
        selected_placements = {
            atom.atom_id: dict(placements.get(atom.atom_id) or {})
            for atom in selected
            if placements.get(atom.atom_id)
        }
        signature = "|".join(atom.atom_id for atom in selected)
        signature += json.dumps(selected_placements, sort_keys=True, ensure_ascii=True)
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
        score_parts = {
            atom.atom_id: {
                key: round(float(value), 6)
                for key, value in ParamSpace._atom_index(
                    atom, atom_stats, total_trials
                ).items()
            }
            for atom in selected
        }
        return MutationSpec(
            mutation_id=f"portfolio::{digest}",
            kind="portfolio" if len(selected) > 1 else selected[0].kind,
            atom=selected[0],
            atoms=selected,
            operation=(
                "apply_mutation_portfolio"
                if len(selected) > 1 else ParamSpace._operation(selected[0])
            ),
            description="; ".join(atom.description for atom in selected),
            score_parts=score_parts,
            placements=selected_placements,
        )

    @staticmethod
    def _atom_index(
        atom: ParamAtom,
        atom_stats: Dict[str, Dict[str, int]],
        total_trials: int,
    ) -> Dict[str, float]:
        stats = atom_stats.get(atom.atom_id, {})
        trials = max(0, int(stats.get("trial_count", 0) or 0))
        successes = max(0, int(stats.get("success_count", 0) or 0))
        failures = max(0, trials - successes)
        q_score = (successes - 0.2 * failures) / trials if trials else 0.0
        ucb_score = math.sqrt(
            math.log(1 + max(1, total_trials)) / (1 + trials)
        )
        return {
            "q": q_score,
            "ucb": ucb_score,
            "score": max(0.0, q_score + SPATIAL_SKILL_GROWTH_UCB_C * ucb_score),
            "trial_count": float(trials),
            "success_count": float(successes),
        }

    @staticmethod
    def _mutation_quality(
        mutation: MutationSpec,
        atom_stats: Dict[str, Dict[str, int]],
    ) -> float:
        total_trials = sum(
            max(0, int(item.get("trial_count", 0) or 0))
            for item in atom_stats.values()
        )
        scores = [
            ParamSpace._atom_index(atom, atom_stats, total_trials)["score"]
            for atom in mutation.selected_atoms
        ]
        return sum(scores) / max(1, len(scores))

    @staticmethod
    def _workflow_quality(workflow: WorkflowSpec, total_trials: int) -> float:
        trials = max(0, workflow.metrics.trial_count)
        successes = max(0, workflow.metrics.correct_count)
        failures = max(0, trials - successes)
        q_score = (
            (successes - 0.2 * failures) / trials
            if trials else 0.0
        )
        ucb_score = math.sqrt(
            math.log(1 + max(1, total_trials)) / (1 + trials)
        )
        return max(0.0, q_score + SPATIAL_SKILL_GROWTH_UCB_C * ucb_score)

    @classmethod
    def _best_coverage(cls, workflows: Iterable[WorkflowSpec]) -> Dict[str, float]:
        workflows = list(workflows)
        total_trials = sum(
            max(0, workflow.metrics.trial_count) for workflow in workflows
        )
        best = {}
        for workflow in workflows:
            quality = cls._workflow_quality(workflow, total_trials)
            for feature in cls.workflow_features(workflow):
                best[feature] = max(best.get(feature, 0.0), quality)
        return best

    @staticmethod
    def _marginal_gain(
        features: Set[str],
        quality: float,
        best_coverage: Dict[str, float],
    ) -> float:
        return sum(
            max(0.0, quality - best_coverage.get(feature, 0.0))
            for feature in features
        )

    @staticmethod
    def _operation(atom: ParamAtom) -> str:
        if atom.kind == "structural":
            return atom.value
        if atom.kind == "numerical":
            return "set_parameter"
        if atom.kind == "fixed":
            return "insert_tool"
        return "set_semantic_parameter"
