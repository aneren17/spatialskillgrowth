"""检测窗口媒体预处理：保留原视频，并为图像工具按固定频率抽帧。"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import List

import cv2

from nodes.mem.spatialskillgrowth.models import TaskRecord


DEFAULT_SAMPLE_FPS = 1.0
DEFAULT_MAX_SAMPLED_FRAMES = 12
DEFAULT_JPEG_QUALITY = 90


class MediaPreprocessor:
    def __init__(
        self,
        output_root: Path,
        sample_fps: float = DEFAULT_SAMPLE_FPS,
        max_sampled_frames: int = DEFAULT_MAX_SAMPLED_FRAMES,
        jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    ):
        self.output_root = Path(output_root)
        self.sample_fps = max(0.1, float(sample_fps))
        self.max_sampled_frames = max(1, int(max_sampled_frames))
        self.jpeg_quality = max(1, min(100, int(jpeg_quality)))

    def prepare(self, task: TaskRecord) -> TaskRecord:
        if len(task.image_paths) != 1:
            return task
        media_path = Path(task.image_paths[0])
        if task.media_type == "image":
            return replace(
                task,
                sampled_frame_paths=[str(media_path)],
                media_metadata={
                    "media_type": "image",
                    "source": str(media_path.resolve()),
                    "sample_fps": 0.0,
                    "sampled_frame_count": 1,
                    "duration_seconds": 0.0,
                },
            )
        if task.media_type != "video":
            return task
        frames, metadata = self._sample_video(media_path, task.task_id)
        return replace(
            task,
            sampled_frame_paths=frames,
            media_metadata=metadata,
        )

    def _sample_video(self, video_path: Path, task_id: str) -> tuple[List[str], dict]:
        output_dir = self.output_root / _safe_component(task_id)
        manifest_path = output_dir / "manifest.json"
        source_stat = video_path.stat()
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                manifest = {}
            cached = [
                str((output_dir / name).resolve())
                for name in manifest.get("frames", [])
                if (output_dir / name).is_file()
            ]
            cache_matches = (
                manifest.get("source") == str(video_path.resolve())
                and int(manifest.get("source_size") or -1) == source_stat.st_size
                and int(manifest.get("source_mtime_ns") or -1)
                == source_stat.st_mtime_ns
                and float(manifest.get("sample_fps") or 0.0) == self.sample_fps
                and int(manifest.get("max_sampled_frames") or 0)
                == self.max_sampled_frames
            )
            if cached and cache_matches:
                return cached, manifest

        output_dir.mkdir(parents=True, exist_ok=True)
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return [], {
                "media_type": "video",
                "source": str(video_path.resolve()),
                "sample_fps": self.sample_fps,
                "sampled_frame_count": 0,
                "duration_seconds": 0.0,
                "error": "OpenCV 无法打开视频。",
            }
        source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / source_fps if source_fps > 0 and frame_count > 0 else 0.0
        timestamps = _sample_timestamps(
            duration,
            self.sample_fps,
            self.max_sampled_frames,
        )
        frames = []
        frame_names = []
        for index, timestamp in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            name = f"frame_{index:03d}_{int(round(timestamp * 1000)):07d}ms.jpg"
            path = output_dir / name
            written = cv2.imwrite(
                str(path),
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
            )
            if written:
                frames.append(str(path.resolve()))
                frame_names.append(name)
        capture.release()
        metadata = {
            "media_type": "video",
            "source": str(video_path.resolve()),
            "source_size": source_stat.st_size,
            "source_mtime_ns": source_stat.st_mtime_ns,
            "source_fps": source_fps,
            "source_frame_count": frame_count,
            "duration_seconds": round(duration, 6),
            "sample_fps": self.sample_fps,
            "max_sampled_frames": self.max_sampled_frames,
            "sampled_frame_count": len(frames),
            "sample_timestamps": timestamps,
            "frames": frame_names,
            "error": "" if frames else "视频中未能抽取有效帧。",
        }
        manifest_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return frames, metadata


def _sample_timestamps(
    duration_seconds: float,
    sample_fps: float,
    max_frames: int,
) -> List[float]:
    if duration_seconds <= 0:
        return [0.0]
    step = 1.0 / sample_fps
    count = max(1, int(math.ceil(duration_seconds / step)))
    timestamps = [min(duration_seconds - 0.001, (index + 0.5) * step) for index in range(count)]
    timestamps = [max(0.0, value) for value in timestamps]
    if len(timestamps) <= max_frames:
        return timestamps
    indices = [
        round(index * (len(timestamps) - 1) / (max_frames - 1))
        for index in range(max_frames)
    ] if max_frames > 1 else [len(timestamps) // 2]
    return [timestamps[index] for index in dict.fromkeys(indices)]


def _safe_component(value: str) -> str:
    output = "".join(
        character if character.isalnum() or character in "_.-" else "_"
        for character in str(value or "")
    ).strip("._")
    return output or "task"
