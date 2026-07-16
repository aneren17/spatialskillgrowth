"""实验状态、轨迹和 JSON 工作流仓库。"""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from nodes.mem.spatialskillgrowth.experiment_config import ExperimentPaths
from nodes.mem.spatialskillgrowth.models import (
    EvidenceDecision,
    RetrievalDecision,
    WorkflowSpec,
    WorkflowStatus,
)
from nodes.mem.spatialskillgrowth.workflow_executor import (
    WorkflowPythonExporter,
    legacy_python_wrapper,
)

class ExperimentStore:
    """SQLite 只保存实验事实；JSON 与 Python Skill 保存在文件仓库。"""

    def __init__(self, paths: ExperimentPaths):
        self.paths = paths
        self.db_path = paths.state_dir / "spatialskillgrowth.db"
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    split_name TEXT NOT NULL DEFAULT '',
                    problem_class TEXT NOT NULL DEFAULT '',
                    question TEXT NOT NULL,
                    groundtruth TEXT NOT NULL DEFAULT '',
                    answer_type TEXT NOT NULL DEFAULT '',
                    final_answer TEXT NOT NULL DEFAULT '',
                    correct INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    summary_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS trials (
                    task_id TEXT NOT NULL,
                    trial_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL DEFAULT '',
                    mutation_mode TEXT NOT NULL DEFAULT '',
                    answer TEXT NOT NULL DEFAULT '',
                    correct INTEGER NOT NULL DEFAULT 0,
                    evidence_accepted INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, trial_id)
                );
                CREATE TABLE IF NOT EXISTS retrievals (
                    task_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, strategy)
                );
                CREATE TABLE IF NOT EXISTS mutation_directions (
                    task_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    direction_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, mode)
                );
                CREATE TABLE IF NOT EXISTS workflow_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    task_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS atom_coverage (
                    problem_class TEXT NOT NULL,
                    atom_id TEXT NOT NULL,
                    trial_count INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(problem_class, atom_id)
                );
                """
            )

    def begin_task(
        self,
        task_id: str,
        mode: str,
        split_name: str,
        problem_class: str,
        question: str,
        groundtruth: str,
        answer_type: str,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, mode, split_name, problem_class, question,
                    groundtruth, answer_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    mode=excluded.mode,
                    split_name=excluded.split_name,
                    problem_class=excluded.problem_class,
                    question=excluded.question,
                    groundtruth=excluded.groundtruth,
                    answer_type=excluded.answer_type,
                    final_answer='', correct=0, completed=0, summary_json='{}',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    task_id,
                    mode,
                    split_name,
                    problem_class,
                    question,
                    groundtruth,
                    answer_type,
                ),
            )
            connection.execute("DELETE FROM trials WHERE task_id=?", (task_id,))

    def is_complete(self, task_id: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT completed FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return bool(row and row["completed"])

    def get_summary(self, task_id: str) -> Optional[Dict]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT summary_json FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return json.loads(row["summary_json"]) if row else None

    def save_trial(
        self,
        task_id: str,
        trial_id: str,
        workflow_id: str,
        mutation_mode: str,
        answer: str,
        correct: bool,
        evidence: EvidenceDecision,
        result: Dict,
    ) -> None:
        payload = {
            "task_id": task_id,
            "trial_id": trial_id,
            "workflow_id": workflow_id,
            "mutation_mode": mutation_mode,
            "answer": answer,
            "correct": bool(correct),
            "evidence": evidence.to_dict(),
            "result": result,
        }
        self.save_trajectory(task_id, trial_id, payload)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO trials(
                    task_id, trial_id, workflow_id, mutation_mode, answer,
                    correct, evidence_accepted, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    trial_id,
                    workflow_id,
                    mutation_mode,
                    answer,
                    int(correct),
                    int(evidence.accepted),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def save_retrieval(self, task_id: str, decision: RetrievalDecision) -> None:
        payload = decision.to_dict()
        _write_json(self.paths.retrieval_root / f"{task_id}.json", payload)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO retrievals VALUES (?, ?, ?)",
                (task_id, decision.strategy, json.dumps(payload, ensure_ascii=False)),
            )

    def save_direction(self, task_id: str, mode: str, direction: Dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO mutation_directions VALUES (?, ?, ?)",
                (task_id, mode, json.dumps(direction, ensure_ascii=False)),
            )

    def record_workflow_event(
        self,
        workflow_id: str,
        task_id: str,
        event_type: str,
        payload: Optional[Dict] = None,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_events(workflow_id, task_id, event_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    task_id,
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )

    def atom_stats(self, problem_class: str) -> Dict[str, Dict[str, int]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT atom_id, trial_count, success_count FROM atom_coverage
                WHERE problem_class=?
                """,
                (problem_class,),
            ).fetchall()
        return {
            str(row["atom_id"]): {
                "trial_count": int(row["trial_count"]),
                "success_count": int(row["success_count"]),
            }
            for row in rows
        }

    def record_atom_results(self, problem_class: str, atom_results: Dict[str, bool]) -> None:
        with self._lock, self._connect() as connection:
            for atom_id, success in atom_results.items():
                connection.execute(
                    """
                    INSERT INTO atom_coverage(
                        problem_class, atom_id, trial_count, success_count
                    ) VALUES (?, ?, 1, ?)
                    ON CONFLICT(problem_class, atom_id) DO UPDATE SET
                        trial_count=trial_count + 1,
                        success_count=success_count + excluded.success_count
                    """,
                    (problem_class, str(atom_id), int(bool(success))),
                )

    def workflow_task_ids(self, workflow_id: str) -> List[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT task_id FROM trials WHERE workflow_id=?",
                (workflow_id,),
            ).fetchall()
        return [str(row["task_id"]) for row in rows]

    def complete_task(self, task_id: str, answer: str, correct: bool, summary: Dict) -> None:
        self.save_trajectory(task_id, "summary", summary)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks SET final_answer=?, correct=?, completed=1,
                    summary_json=?, updated_at=CURRENT_TIMESTAMP WHERE task_id=?
                """,
                (answer, int(correct), json.dumps(summary, ensure_ascii=False), task_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Cannot complete unknown task: {task_id}")
        self._append_result(summary)

    def fail_task(
        self,
        task_id: str,
        mode: str,
        split_name: str,
        problem_class: str,
        question: str,
        groundtruth: str,
        answer_type: str,
        error: str,
    ) -> Dict:
        """持久化异常但保持 completed=0，使 --resume 可以重试。"""
        summary = {
            "task_id": task_id.removeprefix("explore__").removeprefix("infer__"),
            "state_task_id": task_id,
            "mode": mode,
            "split": split_name,
            "problem_class": problem_class,
            "answer_type": answer_type,
            "groundtruth": groundtruth,
            "answer": "",
            "correct": False,
            "failed": True,
            "completed": False,
            "error": error,
        }
        self.save_trajectory(task_id, "error", summary)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, mode, split_name, problem_class, question,
                    groundtruth, answer_type, completed, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    problem_class=excluded.problem_class,
                    summary_json=excluded.summary_json,
                    completed=0,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    task_id,
                    mode,
                    split_name,
                    problem_class,
                    question,
                    groundtruth,
                    answer_type,
                    json.dumps(summary, ensure_ascii=False),
                ),
            )
        path = self.paths.results_root / "errors.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
        return summary

    def save_trajectory(self, task_id: str, name: str, payload: Dict) -> Path:
        path = self.paths.trajectory_root / task_id / f"{name}.json"
        _write_json(path, payload)
        return path

    def _append_result(self, summary: Dict) -> None:
        path = self.paths.results_root / "per_task.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


class WorkflowRepository:
    """JSON 保存检索契约，Python 保存可编辑执行实现。"""

    def __init__(self, paths: ExperimentPaths):
        self.paths = paths
        self._lock = threading.RLock()

    def save(self, workflow: WorkflowSpec) -> Path:
        status = WorkflowStatus(workflow.status)
        root = self._root_for_status(status)
        path = (
            root
            / workflow.applicability.problem_class
            / "workflows"
            / f"{workflow.workflow_id}.json"
        )
        with self._lock:
            existing_script = self.script_path(workflow.workflow_id)
            existing_script_content = (
                existing_script.read_bytes()
                if existing_script is not None and existing_script.is_file()
                else None
            )
            self._remove_from_other_statuses(workflow, status)
            _write_json_atomic(path, workflow.to_dict())
            target_script = path.parents[1] / "scripts" / f"{workflow.workflow_id}.py"
            if not target_script.exists() and existing_script_content is not None:
                target_script.parent.mkdir(parents=True, exist_ok=True)
                target_script.write_bytes(existing_script_content)
            WorkflowPythonExporter(path.parents[1] / "scripts").export(
                workflow,
                force=False,
            )
            self._rebuild_docs(workflow.applicability.problem_class, status)
        return path

    def load(self, path: Path) -> WorkflowSpec:
        return WorkflowSpec.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def get(self, workflow_id: str) -> Optional[WorkflowSpec]:
        for root in self._status_roots().values():
            matches = list(root.glob(f"*/workflows/{workflow_id}.json"))
            if matches:
                return self.load(matches[0])
        return None

    def script_path(self, workflow_id: str) -> Optional[Path]:
        for root in self._status_roots().values():
            matches = list(root.glob(f"*/scripts/{workflow_id}.py"))
            if matches:
                return matches[0]
        return None

    def snapshot_active_from(
        self,
        source: "WorkflowRepository",
        provenance: Optional[Dict] = None,
    ) -> Dict:
        """复制推理所用 active Skill，并使本地快照成为后续唯一读取源。"""
        snapshot_path = self.paths.skill_root / "SOURCE_SNAPSHOT.json"
        requested_source = str(source.paths.root.resolve())
        if snapshot_path.exists():
            existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if existing.get("source_root") != requested_source:
                raise RuntimeError(
                    "Inference run already contains a snapshot from another source: "
                    f"{existing.get('source_root')}"
                )
            return existing
        shutil.copytree(
            source.paths.active_skill_root,
            self.paths.active_skill_root,
            dirs_exist_ok=True,
        )
        migrated_scripts = []
        for workflow in self.list_active():
            script_path = self.script_path(workflow.workflow_id)
            if script_path is None or not script_path.is_file():
                continue
            if legacy_python_wrapper(script_path):
                WorkflowPythonExporter(script_path.parent).export(
                    workflow, force=True
                )
                migrated_scripts.append(workflow.workflow_id)
        source_whiteboard = source.paths.skill_root / "WHITEBOARD.json"
        if source_whiteboard.is_file():
            shutil.copy2(source_whiteboard, self.paths.skill_root / "WHITEBOARD.json")
        files = []
        for path in sorted(self.paths.active_skill_root.rglob("*")):
            if not path.is_file():
                continue
            files.append({
                "path": str(path.relative_to(self.paths.skill_root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        payload = {
            "source_root": requested_source,
            "source_experiment": source.paths.experiment,
            "source_run_id": source.paths.run_id,
            "active_workflow_count": len(self.list_active()),
            "legacy_scripts_migrated": migrated_scripts,
            "files": files,
            **dict(provenance or {}),
        }
        _write_json_atomic(snapshot_path, payload)
        return payload

    def list_active(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.active_skill_root, problem_class)

    def list_provisional(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.provisional_skill_root, problem_class)

    def list_archive(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.archive_skill_root, problem_class)

    def list_retrievable(
        self,
        problem_class: str = "",
        include_provisional: bool = False,
    ) -> List[WorkflowSpec]:
        workflows = self.list_active(problem_class)
        if include_provisional:
            workflows.extend(self.list_provisional(problem_class))
        return workflows

    def transition(
        self,
        workflow: WorkflowSpec,
        status: WorkflowStatus,
        reason: str = "",
    ) -> WorkflowSpec:
        previous_status = WorkflowStatus(workflow.status)
        workflow.status = status.value
        self.save(workflow)
        if reason and status == WorkflowStatus.ARCHIVE:
            metadata = (
                self.paths.archive_skill_root
                / workflow.applicability.problem_class
                / "workflows"
            )
            _write_json_atomic(
                metadata / f"{workflow.workflow_id}.archive.json",
                {"workflow_id": workflow.workflow_id, "reason": reason},
            )
        if previous_status != status:
            self._rebuild_docs(workflow.applicability.problem_class, previous_status)
        return workflow

    def archive(self, workflow: WorkflowSpec, reason: str = "") -> WorkflowSpec:
        return self.transition(workflow, WorkflowStatus.ARCHIVE, reason)

    def update_metrics(
        self,
        workflow: WorkflowSpec,
        task_id: str,
        correct: bool,
        evidence_accepted: bool,
        tool_calls: int,
        tool_failures: int,
        latency_ms: float,
    ) -> WorkflowSpec:
        current = self.get(workflow.workflow_id) or workflow
        metrics = current.metrics
        metrics.trial_count += 1
        metrics.correct_count += int(correct)
        metrics.evidence_accept_count += int(evidence_accepted)
        metrics.total_tool_calls += max(0, int(tool_calls))
        metrics.tool_failure_count += max(0, int(tool_failures))
        metrics.total_latency_ms += max(0.0, float(latency_ms))
        if correct and task_id not in current.source_task_ids:
            current.source_task_ids.append(task_id)
        self.save(current)
        return current

    def _list(self, root: Path, problem_class: str) -> List[WorkflowSpec]:
        pattern = (
            f"{problem_class}/workflows/*.json"
            if problem_class
            else "*/workflows/*.json"
        )
        workflows = []
        for path in sorted(root.glob(pattern)):
            if path.name.endswith(".archive.json"):
                continue
            workflows.append(self.load(path))
        return workflows

    def _rebuild_docs(self, problem_class: str, status: WorkflowStatus) -> None:
        workflows = self._list(self._root_for_status(status), problem_class)
        root = self._root_for_status(status)
        directory = root / problem_class
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "scripts").mkdir(parents=True, exist_ok=True)
        (directory / "workflows").mkdir(parents=True, exist_ok=True)
        metadata_path = directory / "skill.json"
        existing_metadata = {}
        if metadata_path.exists():
            existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        description = str(
            existing_metadata.get("description")
            or next(
                (
                    item.applicability.description
                    for item in workflows
                    if item.applicability.description
                ),
                f"Reusable validated workflows for {problem_class}.",
            )
        )
        title = str(existing_metadata.get("title") or problem_class.replace("_", " ").title())
        lines = [
            "---",
            f"name: {problem_class}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            "---",
            "",
            f"# {title}",
            "",
            "## 用途",
            "",
            description,
            "",
        ]
        event_type = str(existing_metadata.get("event_type") or "")
        display_names = existing_metadata.get("display_names") or {}
        if event_type:
            lines.extend([
                "## 事件接口",
                "",
                f"- 精确 `event_type`：`{event_type}`",
                f"- 主检测工具：`{existing_metadata.get('primary_tool') or 'embeddingTool'}`",
                f"- 答案类型：`{existing_metadata.get('answer_type') or 'bool'}`，输出“是”或“否”",
                "- 结构化结果：必须包含 `is_anomaly` 和 `threshold`",
                "",
            ])
        if isinstance(display_names, dict) and display_names:
            source_titles = {
                "dashboard": "大屏端",
                "rag": "RAG 检索/检测端",
                "stream": "实时视频流检测页",
            }
            lines.extend([
                "## 各端显示名称",
                "",
                "| 来源 | 中文显示名称 |",
                "|---|---|",
            ])
            lines.extend(
                f"| {source_titles.get(source, source)} | {label} |"
                for source, label in display_names.items()
            )
            lines.append("")
        tool_template = existing_metadata.get("tool_template")
        if isinstance(tool_template, dict) and tool_template:
            lines.extend([
                "## 工具调用模板",
                "",
                "```json",
                json.dumps(tool_template, ensure_ascii=False, indent=2),
                "```",
                "",
            ])
        evidence_requirements = existing_metadata.get("evidence_requirements") or []
        if isinstance(evidence_requirements, list) and evidence_requirements:
            lines.extend(["## 证据要求", ""])
            lines.extend(f"- {item}" for item in evidence_requirements)
            lines.append("")
        lines.extend([
            "## 资源",
            "",
            "- `workflows/*.json` 保存可检索的工作流定义。",
            "- `scripts/*.py` 保存实际执行的 Python Skill。",
            "",
            "## 已验证工作流",
            "",
        ])
        if not workflows:
            lines.append("当前运行尚无通过验证的工作流。")
            lines.append("")
        for workflow in sorted(workflows, key=lambda item: item.workflow_id):
            lines.extend([
                f"## {workflow.name or workflow.workflow_id}",
                "",
                f"- id: `{workflow.workflow_id}`",
                f"- 来源工作流：`{workflow.derived_from_workflow_id or '无'}`",
                f"- 变异模式：`{workflow.mutation_mode}`",
                f"- 工具：`{', '.join(step.tool_name for step in workflow.steps)}`",
                f"- 适用范围：{workflow.applicability.description or '未说明'}",
                f"- 排除条件：{workflow.applicability.exclusions or '未说明'}",
                "",
            ])
        (directory / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
        metadata = dict(existing_metadata)
        metadata.update({
            "name": problem_class,
            "title": title,
            "problem_class": problem_class,
            "description": description,
            "status": status.value,
            "workflow_count": len(workflows),
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "path": f"workflows/{workflow.workflow_id}.json",
                    "script": f"scripts/{workflow.workflow_id}.py",
                }
                for workflow in sorted(workflows, key=lambda item: item.workflow_id)
            ],
        })
        _write_json_atomic(metadata_path, metadata)
        self._rebuild_skill_index(root)

    def _remove_from_other_statuses(
        self,
        workflow: WorkflowSpec,
        target_status: WorkflowStatus,
    ) -> None:
        problem_class = workflow.applicability.problem_class
        for status, root in self._status_roots().items():
            if status == target_status:
                continue
            workflow_path = root / problem_class / "workflows" / f"{workflow.workflow_id}.json"
            script_path = root / problem_class / "scripts" / f"{workflow.workflow_id}.py"
            removed = False
            for path in (workflow_path, script_path):
                if path.exists():
                    path.unlink()
                    removed = True
            if removed:
                self._rebuild_docs(problem_class, status)

    def _root_for_status(self, status: WorkflowStatus) -> Path:
        return self._status_roots()[status]

    def _status_roots(self) -> Dict[WorkflowStatus, Path]:
        return {
            WorkflowStatus.ACTIVE: self.paths.active_skill_root,
            WorkflowStatus.PROVISIONAL: self.paths.provisional_skill_root,
            WorkflowStatus.ARCHIVE: self.paths.archive_skill_root,
        }

    @staticmethod
    def _rebuild_skill_index(root: Path) -> None:
        skills = []
        for path in sorted(root.glob("*/skill.json")):
            skills.append(json.loads(path.read_text(encoding="utf-8")))
        _write_json_atomic(root / "SKILLS.json", {"skills": skills})


class TrajectoryRecorder:
    def __init__(self, store: ExperimentStore):
        self.store = store

    def record(self, task_id: str, name: str, payload: Dict) -> Path:
        return self.store.save_trajectory(task_id, name, payload)


def _write_json(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_json_atomic(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
