"""异常检测工作流可变异的工具参数。"""

import hashlib
import json

from nodes.mem.spatialskillgrowth.core.models import MutationSpec
from nodes.mem.spatialskillgrowth.core.models import ParamAtom
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import can_add_tool
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import compatible_producers

# 硬编码的各种预设变异。这也是喂给大模型选的“菜单”。
COMMON_MUTATIONS = (
    ParamAtom(
        "embeddingTool",
        "event_type",
        "runtime_event_type",
        "fixed",
        "使用输入中确定的精确 event_type 进行异常检测。",
        args={"file_path": "$media", "event_type": "$slot.event_type"},
    ),
    ParamAtom("MLLM", "scope", "whole_image", "world_model", "分析完整图像。"),
    ParamAtom("MLLM", "scope", "local_regions", "world_model", "分析已定位的局部区域。"),
    ParamAtom("MLLM", "evidence_focus", "explicit_visual_cues", "world_model", "给出明确视觉线索。"),
    ParamAtom("yoloTool", "threshold", "low", "numerical", "使用 0.3 检测阈值。"),
    ParamAtom("yoloTool", "threshold", "medium", "numerical", "使用 0.5 检测阈值。"),
    ParamAtom("sam3", "threshold", "low", "numerical", "使用 0.3 分割阈值。"),
    ParamAtom("sam3", "threshold", "medium", "numerical", "使用 0.5 分割阈值。"),
    ParamAtom("sam3", "threshold", "high", "numerical", "使用 0.7 分割阈值。"),
    ParamAtom("groundingdino", "box_threshold", "low", "numerical", "使用 0.3 开放词汇检测阈值。"),
    ParamAtom("groundingdino", "box_threshold", "medium", "numerical", "使用 0.5 开放词汇检测阈值。"),
    ParamAtom("paddleOcrTool", "evidence_role", "text_reading", "fixed", "读取可见文字。"),
    ParamAtom("paddleHeadDetTool", "target", "head", "fixed", "检测可见人头。"),
    ParamAtom("paddlePedriderDetTool", "target", "traffic_subject", "fixed", "检测交通参与者。"),
    ParamAtom("crop_detections", "operation", "insert_after_detection", "structural", "裁剪已检测区域。"),
    ParamAtom("picRelativeCut", "operation", "insert_relative_crop", "structural", "保留目标相对布局。"),
    ParamAtom("unidepth", "evidence_role", "metric_depth", "fixed", "估计检测目标深度。"),
    ParamAtom("python_code_sandbox", "operation", "append_verification", "structural", "计算结构化证据摘要。"),
)


class ParamSpace:
    """Director 选方向，本类只生成少量可执行候选并按历史排序。"""

    def __init__(self, extra_atoms=None):
        self.extra_atoms = {}
        self.replace_extra_atoms(extra_atoms or {})

    def replace_extra_atoms(self, extra_atoms):
        self.extra_atoms = {}
        for event_type, atoms in extra_atoms.items():
            self.extra_atoms[str(event_type)] = list(atoms)

    def atoms_for(self, event_type):
        """拉取当前任务能用的全部配置菜单（包括公用菜单和特定异常的额外菜单）。"""
        atoms = list(COMMON_MUTATIONS)
        atoms.extend(self.extra_atoms.get("*", []))
        atoms.extend(self.extra_atoms.get(event_type, []))
        unique = {}
        for atom in atoms:
            unique[atom.atom_id] = atom
        output = []
        for atom_id in sorted(unique):
            output.append(unique[atom_id])
        return output

    def candidate_portfolios(
        self,
        problem_class,
        atom_stats,
        workflow_tools=(),
        allowed_tool_names=None,
        preferred_atom_ids=(),
        avoid_atom_ids=(),
        placements=None,
        atoms_per_portfolio=3,
    ):
        """
        [组装mutation方案]
        (LLM)给出了推荐(preferred)，这里负责把这些散装的推荐打包成一个完整的方案。
        """
        # 1. 过滤：只保留被允许的、在 preferred 列表里的原子。
        allowed_tools = set(allowed_tool_names or [])
        avoided = set(avoid_atom_ids)
        preferred = set(preferred_atom_ids)
        atoms = []
        for atom in self.atoms_for(problem_class):
            if allowed_tools and atom.tool_name not in allowed_tools:
                continue
            if atom.atom_id in avoided:
                continue
            atoms.append(atom)
        # 2. 补齐依赖 (Dependency Resolution)
        # 假设 LLM 说“我要加一个 `crop_detections`(裁剪图片) 工具”。
        # 但是！裁剪工具必须依赖前面有一个目标检测工具(比如 yolo) 圈出了框，否则没法裁！
        # self._add_required_producer 就是自动扫描清单，如果发现缺少前置工具，自动帮它补上。
        directed = []
        for atom in atoms:
            if not preferred or atom.atom_id in preferred:
                directed.append(atom)
        candidates = []
        for atom in directed:
            portfolio = self._add_required_producer(
                atom,
                atoms,
                set(workflow_tools),
                atoms_per_portfolio,
            )
            candidates.append(self._mutation_spec(portfolio, placements or {}))
            
        # 3. 如果有多个推荐，尝试把它们组合起来，一并生成变异规格 (MutationSpec)
        if len(directed) > 1:
            combined = []
            axes = set()
            for atom in directed:
                axis = (atom.tool_name, atom.axis)
                if axis in axes:
                    continue
                combined.append(atom)
                axes.add(axis)
                if len(combined) >= atoms_per_portfolio:
                    break
            if len(combined) > 1:
                candidates.append(self._mutation_spec(combined, placements or {}))

        unique = {}
        for candidate in candidates:
            unique[candidate.mutation_id] = candidate
        return list(unique.values())

    def select_workflow_mutations(
        self,
        candidates,
        parent_workflow,
        active_workflows,
        atom_stats,
        count=3,
        allow_zero_gain=False,
    ):
        parent_tools = set()
        for step in parent_workflow.steps:
            parent_tools.add(step.tool_name)
        ranked = []
        for mutation, workflow in candidates:
            history_score = self._history_score(mutation, atom_stats)
            new_tool_count = 0
            for atom in mutation.selected_atoms:
                if atom.tool_name not in parent_tools:
                    new_tool_count += 1
            score = history_score + 0.1 * new_tool_count
            ranked.append((score, mutation.mutation_id, mutation, workflow))
        ranked.sort(key=lambda item: (-item[0], item[1]))

        output = []
        for item in ranked[:max(1, count)]:
            mutation = item[2]
            mutation.score_parts["selection"] = {
                "history_score": round(item[0], 6),
            }
            output.append((mutation, item[3]))
        return output

    @staticmethod
    def _add_required_producer(atom, atoms, existing_tools, limit):
        selected = [atom]
        final_tools = set(existing_tools)
        final_tools.add(atom.tool_name)
        if can_add_tool(atom.tool_name, final_tools):
            return selected
        producer_names = compatible_producers(atom.tool_name)
        for candidate in atoms:
            if candidate.tool_name not in producer_names:
                continue
            selected.insert(0, candidate)
            final_tools.add(candidate.tool_name)
            if can_add_tool(atom.tool_name, final_tools):
                break
            if len(selected) >= limit:
                break
        return selected[:limit]

    @staticmethod
    def _history_score(mutation, atom_stats):
        total = 0.0
        for atom in mutation.selected_atoms:
            stats = atom_stats.get(atom.atom_id, {})
            trials = int(stats.get("trial_count", 0) or 0)
            successes = int(stats.get("success_count", 0) or 0)
            total += (successes + 1.0) / (trials + 2.0)
        return total / max(1, len(mutation.selected_atoms))

    @staticmethod
    def _mutation_spec(atoms, placements):
        selected = list(atoms)
        selected_placements = {}
        for atom in selected:
            if placements.get(atom.atom_id):
                selected_placements[atom.atom_id] = dict(placements[atom.atom_id])
        signature = "|".join(atom.atom_id for atom in selected)
        signature += json.dumps(selected_placements, sort_keys=True)
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
        kind = selected[0].kind
        if len(selected) > 1:
            kind = "portfolio"
        return MutationSpec(
            mutation_id="portfolio::" + digest,
            kind=kind,
            atom=selected[0],
            atoms=selected,
            operation="apply_mutation_portfolio",
            description="；".join(atom.description for atom in selected),
            placements=selected_placements,
        )
