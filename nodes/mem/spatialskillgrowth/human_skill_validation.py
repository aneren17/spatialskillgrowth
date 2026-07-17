"""人工 SpatialSkillGrowth Skill 的结构、脚本契约和执行验证。"""

from __future__ import annotations

import ast
import inspect
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agents.spatialskillgrowth.online_data import (
    build_anomaly_question,
    detect_media_type,
)
from nodes.mem.spatialskillgrowth.evidence_validator import (
    build_evidence_validator,
)
from nodes.mem.spatialskillgrowth.media_processing import MediaPreprocessor
from nodes.mem.spatialskillgrowth.models import (
    ApplicabilitySpec,
    TaskRecord,
    WorkflowMetrics,
    WorkflowSpec,
    WorkflowStep,
)
from nodes.mem.spatialskillgrowth.python_skill_runtime import (
    PythonSkillExecutor,
    load_skill_script,
)
from nodes.mem.spatialskillgrowth.skill_layout import (
    skill_metadata_path,
    standard_skill_name,
    workflow_reference_directory,
)
from nodes.mem.spatialskillgrowth.tool_runtime import (
    ToolRuntime,
    normalize_workflow_steps,
)


REQUIRED_SCRIPT_PARAMETERS = ("runtime", "question", "image_paths")
ALLOWED_SKILL_ENTRIES = {"SKILL.md", "scripts", "references"}


def validate_human_skill(
    skill_dir: Path,
    script_path: Path,
    media_path: Path,
    event_type: str,
    real_tools: bool = False,
    install: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    skill_dir = Path(skill_dir).resolve()
    script_path = Path(script_path).resolve()
    media_path = Path(media_path).resolve()
    errors = []
    checks = {}
    frontmatter = _validate_skill_directory(skill_dir, errors)
    checks["standard_skill_layout"] = not errors
    namespace = {}
    workflow = None
    declared_tools: Tuple[str, ...] = ()
    if not script_path.is_file():
        errors.append(f"脚本不存在：{script_path}")
    else:
        try:
            namespace = load_skill_script(script_path)
            checks["safe_python_ast"] = True
        except Exception as exc:
            errors.append(f"脚本 AST/加载失败：{type(exc).__name__}: {exc}")
            checks["safe_python_ast"] = False
    if namespace:
        workflow, declared_tools = _validate_script_contract(
            skill_dir,
            script_path,
            namespace,
            frontmatter,
            errors,
        )
    checks["script_contract"] = workflow is not None and not errors
    execution = {}
    evidence = {}
    if workflow is not None and not errors:
        if not media_path.is_file():
            errors.append(f"验证媒体不存在：{media_path}")
        else:
            execution, evidence = _execute_validation(
                workflow,
                script_path,
                media_path,
                event_type,
                declared_tools,
                real_tools,
            )
            if not execution.get("success"):
                errors.append(
                    "脚本执行失败："
                    + str(execution.get("error") or "没有产生最终答案")
                )
            if not evidence.get("accepted"):
                errors.append(
                    "证据验收失败："
                    + str(evidence.get("reason") or "未知原因")
                )
    checks["execution"] = bool(execution.get("success"))
    checks["evidence_contract"] = bool(evidence.get("accepted"))
    installed = False
    if install and workflow is not None and not errors:
        try:
            _install_human_script(
                skill_dir,
                script_path,
                workflow,
                force,
            )
            installed = True
        except Exception as exc:
            errors.append(f"安装失败：{type(exc).__name__}: {exc}")
    return {
        "valid": not errors,
        "skill_dir": str(skill_dir),
        "script_path": str(script_path),
        "workflow_id": workflow.workflow_id if workflow else "",
        "problem_class": (
            workflow.applicability.problem_class if workflow else ""
        ),
        "declared_tools": list(declared_tools),
        "checks": checks,
        "execution": execution,
        "evidence": evidence,
        "installed": installed,
        "errors": errors,
    }


def _validate_skill_directory(
    skill_dir: Path,
    errors: List[str],
) -> Dict[str, str]:
    if not skill_dir.is_dir():
        errors.append(f"Skill 目录不存在：{skill_dir}")
        return {}
    unexpected = sorted(
        path.name for path in skill_dir.iterdir()
        if path.name not in ALLOWED_SKILL_ENTRIES
    )
    if unexpected:
        errors.append(
            "Skill 根目录只允许 SKILL.md、scripts、references；发现："
            + "、".join(unexpected)
        )
    for name in ("SKILL.md", "scripts", "references"):
        path = skill_dir / name
        if not path.exists():
            errors.append(f"缺少必需的标准路径：{path}")
    if not skill_metadata_path(skill_dir).is_file():
        errors.append("缺少 references/skill.json。")
    if not workflow_reference_directory(skill_dir).is_dir():
        errors.append("缺少 references/workflows/。")
    frontmatter = _parse_frontmatter(skill_dir / "SKILL.md", errors)
    name = str(frontmatter.get("name") or "")
    if name and name != skill_dir.name:
        errors.append(
            f"SKILL.md name={name!r} 必须与目录名 {skill_dir.name!r} 一致。"
        )
    if name:
        try:
            if standard_skill_name(name) != name:
                errors.append(f"Skill 名称不是标准小写连字符格式：{name}")
        except ValueError as exc:
            errors.append(str(exc))
    return frontmatter


def _parse_frontmatter(path: Path, errors: List[str]) -> Dict[str, str]:
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append("SKILL.md 必须以 YAML frontmatter 的 `---` 开始。")
        return {}
    try:
        end = next(
            index for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        errors.append("SKILL.md frontmatter 缺少结束 `---`。")
        return {}
    values = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"无法解析 frontmatter 行：{line}")
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        try:
            value = json.loads(raw) if raw.startswith(('"', "'")) else raw
        except json.JSONDecodeError:
            value = raw.strip("\"'")
        values[key] = str(value)
    if set(values) != {"name", "description"}:
        errors.append("SKILL.md frontmatter 只能且必须包含 name、description。")
    if not values.get("description", "").strip():
        errors.append("SKILL.md description 不能为空。")
    return values


def _validate_script_contract(
    skill_dir: Path,
    script_path: Path,
    namespace: Dict[str, Any],
    frontmatter: Dict[str, str],
    errors: List[str],
) -> tuple[WorkflowSpec | None, Tuple[str, ...]]:
    workflow_id = str(namespace.get("WORKFLOW_ID") or "")
    problem_class = str(namespace.get("PROBLEM_CLASS") or "")
    declared_tools = tuple(
        str(item) for item in (namespace.get("DECLARED_TOOLS") or ())
        if str(item)
    )
    if not workflow_id:
        errors.append("脚本必须声明 WORKFLOW_ID。")
    if workflow_id and script_path.stem != workflow_id:
        errors.append("脚本文件名必须等于 WORKFLOW_ID，例如 <WORKFLOW_ID>.py。")
    if not problem_class:
        errors.append("脚本必须声明 PROBLEM_CLASS。")
    if problem_class and standard_skill_name(problem_class) != skill_dir.name:
        errors.append("PROBLEM_CLASS 与 Skill 目录不匹配。")
    if not declared_tools:
        errors.append("脚本必须声明非空 DECLARED_TOOLS。")
    solve = namespace.get("solve")
    if not callable(solve):
        errors.append("脚本必须定义 solve(runtime, question, image_paths, ...) 函数。")
    else:
        parameters = tuple(inspect.signature(solve).parameters)
        if parameters[:3] != REQUIRED_SCRIPT_PARAMETERS:
            errors.append(
                "solve 的前三个参数必须依次为 runtime、question、image_paths。"
            )
    workflow_path = (
        workflow_reference_directory(skill_dir) / f"{workflow_id}.json"
    )
    contract = namespace.get("WORKFLOW_CONTRACT")
    workflow = None
    if workflow_path.is_file():
        workflow = WorkflowSpec.from_dict(
            json.loads(workflow_path.read_text(encoding="utf-8"))
        )
        if isinstance(contract, dict):
            embedded_workflow = _workflow_from_contract(contract)
            if _stable_contract(embedded_workflow) != _stable_contract(workflow):
                errors.append(
                    "脚本 WORKFLOW_CONTRACT 与 references/workflows 中的契约不一致。"
                )
    elif isinstance(contract, dict):
        workflow = _workflow_from_contract(contract)
    else:
        errors.append(
            "新人工脚本必须声明 WORKFLOW_CONTRACT；已有脚本也可使用"
            " references/workflows/<WORKFLOW_ID>.json。"
        )
    if workflow is None:
        return None, declared_tools
    if workflow.workflow_id != workflow_id:
        errors.append("WORKFLOW_CONTRACT/reference 中的 workflow_id 不一致。")
    if workflow.applicability.problem_class != problem_class:
        errors.append("工作流契约中的 problem_class 与 PROBLEM_CLASS 不一致。")
    graph_tools = tuple(dict.fromkeys(
        step.tool_name for step in workflow.steps
    ))
    if set(graph_tools) != set(declared_tools):
        errors.append("DECLARED_TOOLS 必须与工作流契约中的工具集合完全一致。")
    if set(workflow.applicability.required_tools) != set(declared_tools):
        errors.append("工作流 required_tools 必须与 DECLARED_TOOLS 完全一致。")
    calls = _runtime_calls(script_path)
    called_tools = {item[0] for item in calls}
    called_step_ids = {item[1] for item in calls}
    contract_step_ids = {step.step_id for step in normalize_workflow_steps(
        workflow.steps
    )}
    if called_tools != set(declared_tools):
        errors.append("脚本 runtime.call 工具集合与 DECLARED_TOOLS 不一致。")
    if called_step_ids != contract_step_ids:
        errors.append("脚本 runtime.call 的 step_id 与工作流契约不一致。")
    if frontmatter.get("name") != standard_skill_name(problem_class):
        errors.append("SKILL.md name 与脚本 PROBLEM_CLASS 不一致。")
    required_slots = set(workflow.applicability.required_slots)
    if solve:
        solve_parameters = inspect.signature(solve).parameters
        missing_slots = required_slots.difference(solve_parameters)
        if missing_slots:
            errors.append(
                "solve 缺少工作流必需槽位参数："
                + "、".join(sorted(missing_slots))
            )
    return workflow, declared_tools


def _workflow_from_contract(contract: Dict[str, Any]) -> WorkflowSpec:
    problem_class = str(contract.get("problem_class") or "")
    steps = [
        WorkflowStep.from_dict(item)
        for item in contract.get("steps", [])
        if isinstance(item, dict)
    ]
    steps = normalize_workflow_steps(steps)
    metrics = WorkflowMetrics(
        structural_coverage=float(
            len({step.tool_name for step in steps})
            + sum(len(step.depends_on) for step in steps)
        )
    )
    return WorkflowSpec(
        workflow_id=str(contract.get("workflow_id") or ""),
        name=str(contract.get("name") or "manual_workflow"),
        applicability=ApplicabilitySpec(
            problem_class=problem_class,
            required_slots=list(contract.get("required_slots") or []),
            required_tools=list(contract.get("required_tools") or []),
            answer_types=list(contract.get("answer_types") or ["bool"]),
            description=str(contract.get("description") or ""),
            exclusions=str(contract.get("exclusions") or ""),
            capability_boundary=str(
                contract.get("capability_boundary") or ""
            ),
        ),
        steps=steps,
        status="active",
        mutation_mode="manual",
        metrics=metrics,
    )


def _stable_contract(workflow: WorkflowSpec) -> Dict[str, Any]:
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "problem_class": workflow.applicability.problem_class,
        "required_slots": list(workflow.applicability.required_slots),
        "required_tools": list(workflow.applicability.required_tools),
        "answer_types": list(workflow.applicability.answer_types),
        "description": workflow.applicability.description,
        "exclusions": workflow.applicability.exclusions,
        "capability_boundary": workflow.applicability.capability_boundary,
        "steps": [step.to_dict() for step in workflow.steps],
    }


def _runtime_calls(script_path: Path) -> List[Tuple[str, str]]:
    tree = ast.parse(
        script_path.read_text(encoding="utf-8"),
        filename=str(script_path),
    )
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "runtime"
            and function.attr == "call"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            continue
        step_id = ""
        for keyword in node.keywords:
            if keyword.arg == "step_id" and isinstance(keyword.value, ast.Constant):
                step_id = str(keyword.value.value)
        calls.append((str(node.args[0].value), step_id))
    return calls


def _execute_validation(
    workflow: WorkflowSpec,
    script_path: Path,
    media_path: Path,
    event_type: str,
    declared_tools: Tuple[str, ...],
    real_tools: bool,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    media_type = detect_media_type(str(media_path))
    task = TaskRecord(
        task_id="human_skill_validation",
        question=build_anomaly_question(event_type, media_type),
        groundtruth="是",
        image_paths=[str(media_path)],
        capability=event_type,
        answer_type="bool",
        media_type=media_type,
    )
    with tempfile.TemporaryDirectory() as root:
        task = MediaPreprocessor(Path(root)).prepare(task)
        visual_paths = task.visual_paths
        representative_image = (
            visual_paths[len(visual_paths) // 2]
            if visual_paths else task.media_path
        )
        runtime = ToolRuntime() if real_tools else ToolRuntime(
            _mock_registry(declared_tools, representative_image)
        )
        result = PythonSkillExecutor(runtime).execute(
            script_path,
            workflow,
            task.question,
            visual_paths,
            {"event_type": event_type},
            media_path=task.media_path,
        )
    answer = str(result.get("final_answer") or "")
    decision = build_evidence_validator("none", None).validate(
        workflow.applicability.problem_class,
        task.question,
        answer,
        "bool",
        result,
        [task.media_path],
    )
    return result, decision.to_dict()


class _MockTool:
    def __init__(self, name: str, output):
        self.name = name
        self.output = output

    def invoke(self, args):
        return self.output(args) if callable(self.output) else self.output


def _mock_registry(
    declared_tools: Tuple[str, ...],
    image_path: str,
) -> Dict[str, _MockTool]:
    detections = json.dumps({
        "status": "success",
        "file": image_path,
        "detections": [{
            "class_name": "banner",
            "bbox": [1, 1, 10, 10],
            "score": 0.9,
        }],
    }, ensure_ascii=False)
    outputs = {
        "embeddingTool": "是 (判定阈值: 0.66)",
        "MLLM": "是",
        "paddleOcrTool": "示例横幅文字",
        "yoloTool": detections,
        "groundingdino": detections,
        "sam3": detections,
        "paddleHeadDetTool": detections,
        "paddlePedriderDetTool": detections,
        "crop_detections": json.dumps({
            "status": "success", "file": image_path
        }, ensure_ascii=False),
        "picRelativeCut": json.dumps({
            "status": "success", "file": image_path
        }, ensure_ascii=False),
        "unidepth": detections,
        "python_code_sandbox": "是",
    }
    return {
        name: _MockTool(name, outputs.get(name, "是"))
        for name in declared_tools
    }


def _install_human_script(
    skill_dir: Path,
    script_path: Path,
    workflow: WorkflowSpec,
    force: bool,
) -> None:
    target_script = skill_dir / "scripts" / f"{workflow.workflow_id}.py"
    target_workflow = (
        workflow_reference_directory(skill_dir)
        / f"{workflow.workflow_id}.json"
    )
    if target_script.exists() and target_script.resolve() != script_path:
        if not force:
            raise FileExistsError(
                f"目标脚本已存在：{target_script}；如需覆盖请使用 --force。"
            )
    target_script.parent.mkdir(parents=True, exist_ok=True)
    target_workflow.parent.mkdir(parents=True, exist_ok=True)
    if target_script.resolve() != script_path:
        shutil.copy2(script_path, target_script)
    target_workflow.write_text(
        json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata_path = skill_metadata_path(skill_dir)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    workflows = [
        item for item in metadata.get("workflows", [])
        if item.get("workflow_id") != workflow.workflow_id
    ]
    workflows.append({
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "path": f"references/workflows/{workflow.workflow_id}.json",
        "script": f"scripts/{workflow.workflow_id}.py",
        "authorship": "human",
    })
    metadata.update({
        "workflow_count": len(workflows),
        "workflows": sorted(workflows, key=lambda item: item["workflow_id"]),
    })
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index_path = skill_dir.parent / "SKILLS.json"
    if index_path.exists():
        skills = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(
                skill_dir.parent.glob("*/references/skill.json")
            )
        ]
        index_path.write_text(
            json.dumps({"skills": skills}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
