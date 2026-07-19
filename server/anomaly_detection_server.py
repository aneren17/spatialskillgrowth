"""接收一个媒体文件和异常类别，调用冻结推理架构。"""

import os
import tempfile
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from pydantic import BaseModel

from agents.spatialskillgrowth.anomaly_detection_agent import (
    SpatialSkillGrowthAnomalyDetectionAgent,
)
from agents.spatialskillgrowth.online_data import IMAGE_SUFFIXES
from agents.spatialskillgrowth.online_data import VIDEO_SUFFIXES
from agents.spatialskillgrowth.online_data import resolve_event_type
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_BASE_URL
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE
from config.spatialskillgrowth_config import (
    SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
)
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY
from model.QwenFactory.pureQwenFactory import MultimodalChatOpenAI
from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.core.anomaly_events import (
    class_metadata_for_anomaly,
)
from nodes.mem.spatialskillgrowth.core.experiment_config import DEFAULT_RESULT_ROOT
from nodes.mem.spatialskillgrowth.core.experiment_config import DEFAULT_SEED
from nodes.mem.spatialskillgrowth.core.experiment_config import ExperimentPaths
from nodes.mem.spatialskillgrowth.core.experiment_config import (
    build_experiment_config,
)
from nodes.mem.spatialskillgrowth.pipeline.orchestrator import ExperimentFactory
from nodes.mem.spatialskillgrowth.storage.growth_store import WorkflowRepository


load_dotenv()

API_RUN_ID = os.getenv("SPATIAL_SKILL_GROWTH_API_RUN_ID", "api_server")
API_RESULT_ROOT = os.getenv(
    "SPATIAL_SKILL_GROWTH_API_RESULT_ROOT",
    DEFAULT_RESULT_ROOT,
)
API_SOURCE_RUN_ID = os.getenv("SPATIAL_SKILL_GROWTH_API_SOURCE_RUN_ID", "")
API_SOURCE_RESULT_ROOT = os.getenv(
    "SPATIAL_SKILL_GROWTH_API_SOURCE_RESULT_ROOT",
    API_RESULT_ROOT,
)
API_MAX_REACT_STEPS = int(
    os.getenv("SPATIAL_SKILL_GROWTH_API_MAX_REACT_STEPS", "8")
)
API_MAX_UPLOAD_BYTES = int(
    os.getenv("SPATIAL_SKILL_GROWTH_API_MAX_UPLOAD_BYTES", str(256 * 1024 * 1024))
)
UPLOAD_CHUNK_BYTES = 1024 * 1024
SUPPORTED_MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES

AGENT = None
AGENT_LOCK = threading.Lock()


class DetectionResponse(BaseModel):
    is_anomaly: int
    threshold: float


app = FastAPI(
    title="SpatialSkillGrowth 异常检测服务",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.post("/detect", response_model=DetectionResponse)
def detect_anomaly(
    file: UploadFile = File(...),
    event_type: str = Form(...),
):
    try:
        normalized_event_type = resolve_event_type(event_type)
        temporary_path = _save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        task_id = "api__" + uuid.uuid4().hex
        result = _get_agent().detect(
            temporary_path,
            normalized_event_type,
            task_id=task_id,
        )
        return _build_response(result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="异常检测执行失败：" + str(exc),
        ) from exc
    finally:
        Path(temporary_path).unlink(missing_ok=True)


def _save_upload(file):
    suffix = Path(str(file.filename or "")).suffix.lower()
    if suffix not in SUPPORTED_MEDIA_SUFFIXES:
        raise ValueError("不支持的媒体类型：" + (suffix or "无扩展名"))

    temporary = tempfile.NamedTemporaryFile(
        prefix="spatialskillgrowth_",
        suffix=suffix,
        delete=False,
    )
    temporary_path = temporary.name
    total_bytes = 0
    try:
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > API_MAX_UPLOAD_BYTES:
                raise ValueError(
                    "上传文件超过大小限制："
                    + str(API_MAX_UPLOAD_BYTES)
                    + " bytes"
                )
            temporary.write(chunk)
    except Exception:
        temporary.close()
        Path(temporary_path).unlink(missing_ok=True)
        raise
    temporary.close()
    if total_bytes == 0:
        Path(temporary_path).unlink(missing_ok=True)
        raise ValueError("上传文件不能为空。")
    return temporary_path


def _get_agent():
    global AGENT

    if AGENT is not None:
        return AGENT
    with AGENT_LOCK:
        if AGENT is None:
            AGENT = _build_agent()
    return AGENT


def _build_agent():
    event_types = list(ANOMALY_EVENT_TYPES)
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config(DEFAULT_SEED)
    paths = ExperimentPaths(
        API_RUN_ID,
        API_RESULT_ROOT,
        problem_classes=event_types,
        class_metadata=metadata,
    )
    resume = (paths.root / "manifest.json").is_file()
    paths.ensure(config, "infer", resume=resume)

    repository = WorkflowRepository(paths)
    if API_SOURCE_RUN_ID:
        source_paths = ExperimentPaths(
            API_SOURCE_RUN_ID,
            API_SOURCE_RESULT_ROOT,
            problem_classes=event_types,
            class_metadata=metadata,
        )
        if not source_paths.active_skill_root.is_dir():
            raise FileNotFoundError(
                "探索 Skill 运行不存在：" + str(source_paths.root)
            )
        repository.snapshot_active_from(WorkflowRepository(source_paths))

    llm = MultimodalChatOpenAI(
        base_url=SPATIAL_SKILL_GROWTH_BASE_URL,
        model_name=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE,
        api_key=DEFAULT_API_KEY,
        timeout=SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
        temperature=SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE,
    )
    pipeline = ExperimentFactory(
        config,
        paths,
        llm,
        source_repository=repository,
        max_react_steps=API_MAX_REACT_STEPS,
    ).build_inference()
    return SpatialSkillGrowthAnomalyDetectionAgent(pipeline)


def _build_response(result):
    embedding_is_anomaly = result.get("is_anomaly")
    threshold = _numeric_threshold(result.get("threshold"))

    if embedding_is_anomaly is True:
        if threshold is None:
            raise HTTPException(status_code=502, detail="embeddingTool 未返回有效阈值。")
        return DetectionResponse(is_anomaly=1, threshold=threshold)

    if _other_tools_detected_anomaly(result):
        return DetectionResponse(is_anomaly=1, threshold=1.0)

    if embedding_is_anomaly is False:
        if threshold is None:
            raise HTTPException(status_code=502, detail="embeddingTool 未返回有效阈值。")
        return DetectionResponse(is_anomaly=0, threshold=threshold)

    raise HTTPException(
        status_code=502,
        detail=str(result.get("error") or "推理结果缺少明确的异常判断。"),
    )


def _other_tools_detected_anomaly(result):
    for attempt in result.get("attempts") or []:
        if not attempt.get("success"):
            continue
        if not _is_positive_answer(attempt.get("answer")):
            continue
        successful_tools = set(attempt.get("successful_tools") or [])
        successful_tools.discard("embeddingTool")
        if successful_tools:
            return True
    return False


def _is_positive_answer(value):
    return str(value or "").strip().lower() in {"是", "yes", "true", "1"}


def _numeric_threshold(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None
