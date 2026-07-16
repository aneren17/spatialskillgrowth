"""从一个 banner 视频均匀抽取图片并生成异常检测探索数据集。"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import cv2


DEFAULT_SOURCE = Path("test/banner.mp4")
DEFAULT_OUTPUT = Path("benchmark/anomaly/banner_demo")
DEFAULT_SAMPLE_COUNT = 10
DEFAULT_EVENT_TYPE = "banner"
DEFAULT_GROUNDTRUTH = "是"
DEFAULT_JPEG_QUALITY = 90


def build_dataset(
    source: Path,
    output: Path,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
    force: bool = False,
) -> Path:
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"源视频不存在：{source}")
    if output.exists():
        if not force:
            raise FileExistsError(f"输出目录已存在：{output}；如需重建请使用 --force。")
        shutil.rmtree(output)
    image_root = output / "images"
    image_root.mkdir(parents=True)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV 无法打开视频：{source}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or frame_count <= 0:
        capture.release()
        raise RuntimeError("视频缺少有效 FPS 或帧数信息。")
    duration = frame_count / fps
    records = []
    for index in range(max(1, int(sample_count))):
        timestamp = duration * (index + 0.5) / sample_count
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            continue
        filename = f"banner_{index:02d}_{int(round(timestamp * 1000)):05d}ms.jpg"
        image_path = image_root / filename
        if not cv2.imwrite(
            str(image_path),
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, DEFAULT_JPEG_QUALITY],
        ):
            continue
        records.append({
            "task_id": f"banner_demo_{index:02d}",
            "image_path": filename,
            "event_type": DEFAULT_EVENT_TYPE,
            "answer": DEFAULT_GROUNDTRUTH,
            "answer_type": "bool",
            "metadata": {
                "source_video": str(source),
                "timestamp_seconds": round(timestamp, 6),
                "demo_dataset": True,
            },
        })
    capture.release()
    if len(records) != sample_count:
        raise RuntimeError(
            f"计划生成 {sample_count} 条数据，实际只生成 {len(records)} 条。"
        )
    dataset_path = output / "explore.json"
    dataset_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "source_video": str(source),
        "event_type": DEFAULT_EVENT_TYPE,
        "groundtruth": DEFAULT_GROUNDTRUTH,
        "sample_count": len(records),
        "source_fps": fps,
        "source_frame_count": frame_count,
        "duration_seconds": round(duration, 6),
        "dataset": str(dataset_path),
        "image_root": str(image_root),
        "note": "演示数据：十条样本来自同一视频，不可用于评估泛化能力。",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dataset_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    dataset = build_dataset(
        args.source,
        args.output,
        args.sample_count,
        args.force,
    )
    print(f"已生成 banner 演示数据集：{dataset}")


if __name__ == "__main__":
    main()
