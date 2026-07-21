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
        "使用当前图片和精确 event_type 进行异常检测。",
        args={"file_path": "$image", "event_type": "$slot.event_type"},
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
        {
            "objective": "目标太小没检测出来，需要降低 yolo 的检测阈值",
            "preferred_atom_ids": ["yoloTool:threshold:low"],
            "avoid_atom_ids": ["MLLM:scope:whole_image"],
            "tool_hints": {}
        }
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
        """
        [变异方案选拔]
        因为算力有限（budget=count），不能把所有变异方案都试一遍。
        优先选择能够补充新工具、参数轴、参数原子或工具衔接边的方案。
        """
        best_coverage = self._best_coverage(active_workflows)
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

            features = self.workflow_features(workflow)
            features = features.difference(parent_features)
            if not features:
                continue
            history_score = self._history_score(mutation, atom_stats)
            coverage_gain = self._marginal_gain(
                features,
                history_score,
                best_coverage,
            )
            ranked_candidates.append(
                (mutation, workflow, features, history_score, coverage_gain)
            )

        output = []
        for _ in range(max(1, count)):
            if not ranked_candidates:
                break
            ranked_candidates.sort(
                key=lambda item: (-item[4], -item[3], item[0].mutation_id)
            )
            best = ranked_candidates[0]
            if best[4] <= 0 and not allow_zero_gain:
                break

            mutation, workflow, features, history_score, coverage_gain = (
                ranked_candidates.pop(0)
            )
            mutation.score_parts["workflow"] = {
                "history_score": round(history_score, 6),
                "coverage_gain": round(coverage_gain, 6),
                "feature_count": float(len(features)),
            }
            output.append((mutation, workflow))

            for feature in features:
                previous = best_coverage.get(feature, 0.0)
                best_coverage[feature] = max(previous, history_score)
            updated = []
            for item in ranked_candidates:
                new_gain = self._marginal_gain(
                    item[2],
                    item[3],
                    best_coverage,
                )
                updated.append((item[0], item[1], item[2], item[3], new_gain))
            ranked_candidates = updated
        return output

    @staticmethod
    def workflow_features(workflow):
        """提取用于多样性比较的工具、参数和工具衔接特征。"""
        features = set()
        step_tools = {}
        for step in workflow.steps:
            step_tools[step.step_id] = step.tool_name
        for step in workflow.steps:
            features.add("tool:" + step.tool_name)
            for atom in step.param_atoms:
                features.add("axis:" + atom.tool_name + ":" + atom.axis)
                features.add("atom:" + atom.atom_id)
            for dependency in step.depends_on:
                producer = step_tools.get(dependency)
                if producer:
                    features.add(
                        "edge:" + producer + "->" + step.tool_name
                    )
        return features

    @classmethod
    def _best_coverage(cls, workflows):
        """记录现有工作流对每个特征已经达到的最好历史质量。"""
        best = {}
        for workflow in workflows:
            quality = cls._workflow_quality(workflow)
            for feature in cls.workflow_features(workflow):
                previous = best.get(feature, 0.0)
                best[feature] = max(previous, quality)
        return best

    @staticmethod
    def _workflow_quality(workflow):
        """使用平滑准确率衡量已有工作流质量，不重新引入旧版 UCB。"""
        trials = max(0, int(workflow.metrics.trial_count))
        successes = max(0, int(workflow.metrics.correct_count))
        return (successes + 1.0) / (trials + 2.0)

    @staticmethod
    def _marginal_gain(features, quality, best_coverage):
        gain = 0.0
        for feature in features:
            gain += max(0.0, quality - best_coverage.get(feature, 0.0))
        return gain

    @staticmethod
    def _add_required_producer(atom, atoms, existing_tools, limit):
        """
        [自动依赖注入逻辑]
        如果一个工具需要先导数据，比如 crop 需要 bounding box，这里负责从库里找一个能产出 bounding box 的工具(如 yolo) 垫在前面。
        """
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
        """
        [历史概率打分]
        使用平滑后的成功率公式：(successes + 1) / (trials + 2)。
        拉普拉斯平滑，能防止那种只试了1次而且成功了的原子，击败试了100次成功90次的原子。
        """
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
