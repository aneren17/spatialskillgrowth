"""从 test/corpus 中为每个异常检测 Skill 构建小型 benchmark 数据集。"""

import argparse
import json
import os
import shutil
from pathlib import Path

import cv2

from nodes.mem.spatialskillgrowth.core.anomaly_events import (
    ANOMALY_CLASS_METADATA,
    ANOMALY_EVENT_TYPES,
)
from nodes.mem.spatialskillgrowth.skills.skill_layout import standard_skill_name


DEFAULT_SOURCE_ROOT = "test/corpus"
DEFAULT_OUTPUT_ROOT = "benchmark/anomaly/skill_datasets"
DEFAULT_IMAGE_COUNT = 10
DEFAULT_VIDEO_COUNT = 2
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
POSITIVE_ANSWER = "是"
NEGATIVE_ANSWER = "否"
JSON_INDENT = 2
JPEG_QUALITY = 95


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="按异常事件类别构建可直接用于探索的小型 benchmark。"
    )
    parser.add_argument(
        "--source-root",
        default=DEFAULT_SOURCE_ROOT,
        help="原始数据根目录，默认是 test/corpus。",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="输出根目录。",
    )
    parser.add_argument(
        "--image-count",
        type=int,
        default=DEFAULT_IMAGE_COUNT,
        help="每个类别保留的图片总数。",
    )
    parser.add_argument(
        "--video-count",
        type=int,
        default=DEFAULT_VIDEO_COUNT,
        help="每个类别保留的视频总数。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="输出目录已存在时先删除并重新构建。",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="不生成数据，只验证已有输出。",
    )
    return parser.parse_args()


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=JSON_INDENT)
        handle.write("\n")


def list_media_files(directory, suffixes):
    if not directory.is_dir():
        return []
    files = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append(path)
    files.sort(key=lambda item: item.name)
    return files


def balanced_counts(total):
    positive_count = (total + 1) // 2
    negative_count = total // 2
    return positive_count, negative_count


def evenly_spaced_candidates(files, count):
    if count <= 0:
        return []
    if len(files) < count:
        raise ValueError(
            "候选文件不足：需要 "
            + str(count)
            + " 个，实际只有 "
            + str(len(files))
            + " 个。"
        )
    if count == 1:
        return [files[len(files) // 2]]

    selected = []
    selected_paths = set()
    last_index = len(files) - 1
    for position in range(count):
        index = round(position * last_index / (count - 1))
        path = files[index]
        selected.append(path)
        selected_paths.add(path)
    for path in files:
        if path not in selected_paths:
            selected.append(path)
    return selected


def image_is_readable(path):
    image = cv2.imread(str(path))
    return image is not None and image.size > 0


def video_is_readable(path):
    capture = cv2.VideoCapture(str(path))
    opened = capture.isOpened()
    success = False
    if opened:
        success, frame = capture.read()
        success = success and frame is not None and frame.size > 0
    capture.release()
    return success


def select_readable_files(files, count, media_type):
    if count == 0:
        return []
    candidates = evenly_spaced_candidates(files, count)
    selected = []
    for path in candidates:
        readable = False
        if media_type == "image":
            readable = image_is_readable(path)
        if media_type == "video":
            readable = video_is_readable(path)
        if readable:
            selected.append(path)
        if len(selected) == count:
            return selected
    raise ValueError(
        media_type + " 可读文件不足：需要 " + str(count) + " 个。"
    )


def relative_source_path(path, source_root):
    return path.relative_to(source_root).as_posix()


def copy_image_tasks(
    event_type,
    label_name,
    source_files,
    destination_directory,
    source_root,
    start_index,
):
    tasks = []
    for offset, source_path in enumerate(source_files):
        number = start_index + offset
        destination_name = (
            event_type
            + "_image_"
            + label_name
            + "_"
            + str(number).zfill(2)
            + source_path.suffix.lower()
        )
        destination_path = destination_directory / destination_name
        shutil.copy2(source_path, destination_path)
        answer = POSITIVE_ANSWER
        if label_name == "negative":
            answer = NEGATIVE_ANSWER
        tasks.append(
            {
                "task_id": event_type
                + "__image_"
                + label_name
                + "_"
                + str(number).zfill(2),
                "media_path": "media/images/" + destination_name,
                "event_type": event_type,
                "answer": answer,
                "answer_type": "bool",
                "metadata": {
                    "source_path": relative_source_path(source_path, source_root),
                    "source_label": label_name,
                    "generated_from_video": False,
                },
            }
        )
    return tasks


def extract_frame(source_path, destination_path):
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        capture.release()
        raise ValueError("无法打开视频：" + str(source_path))

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_index = 0
    if frame_count > 1:
        frame_index = frame_count // 2
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame = capture.read()
    if not success or frame is None:
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_index = 0
        success, frame = capture.read()
    capture.release()
    if not success or frame is None:
        raise ValueError("无法从视频读取画面：" + str(source_path))

    written = cv2.imwrite(
        str(destination_path),
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY],
    )
    if not written:
        raise ValueError("无法写入截帧图片：" + str(destination_path))

    timestamp_seconds = 0.0
    if fps > 0:
        timestamp_seconds = frame_index / fps
    return frame_index, round(timestamp_seconds, 3)


def extract_image_tasks(
    event_type,
    label_name,
    source_videos,
    destination_directory,
    source_root,
    start_index,
):
    tasks = []
    for offset, source_path in enumerate(source_videos):
        number = start_index + offset
        destination_name = (
            event_type
            + "_image_"
            + label_name
            + "_"
            + str(number).zfill(2)
            + ".jpg"
        )
        destination_path = destination_directory / destination_name
        frame_index, timestamp_seconds = extract_frame(
            source_path,
            destination_path,
        )
        answer = POSITIVE_ANSWER
        if label_name == "negative":
            answer = NEGATIVE_ANSWER
        tasks.append(
            {
                "task_id": event_type
                + "__image_"
                + label_name
                + "_"
                + str(number).zfill(2),
                "media_path": "media/images/" + destination_name,
                "event_type": event_type,
                "answer": answer,
                "answer_type": "bool",
                "metadata": {
                    "source_path": relative_source_path(source_path, source_root),
                    "source_label": label_name,
                    "generated_from_video": True,
                    "source_frame_index": frame_index,
                    "source_timestamp_seconds": timestamp_seconds,
                },
            }
        )
    return tasks


def copy_video_tasks(
    event_type,
    label_name,
    source_files,
    destination_directory,
    source_root,
    start_index,
):
    tasks = []
    for offset, source_path in enumerate(source_files):
        number = start_index + offset
        destination_name = (
            event_type
            + "_video_"
            + label_name
            + "_"
            + str(number).zfill(2)
            + source_path.suffix.lower()
        )
        destination_path = destination_directory / destination_name
        shutil.copy2(source_path, destination_path)
        answer = POSITIVE_ANSWER
        if label_name == "negative":
            answer = NEGATIVE_ANSWER
        tasks.append(
            {
                "task_id": event_type
                + "__video_"
                + label_name
                + "_"
                + str(number).zfill(2),
                "media_path": "media/videos/" + destination_name,
                "event_type": event_type,
                "answer": answer,
                "answer_type": "bool",
                "metadata": {
                    "source_path": relative_source_path(source_path, source_root),
                    "source_label": label_name,
                    "generated_from_video": False,
                },
            }
        )
    return tasks


def read_source_description(source_root, event_type):
    directory = source_root / (event_type + "3")
    if not directory.is_dir():
        return ""
    text_files = sorted(directory.glob("*.txt"))
    if not text_files:
        return ""
    return text_files[0].read_text(encoding="utf-8").strip()


def build_event_dataset(
    source_root,
    output_root,
    event_type,
    image_count,
    video_count,
):
    skill_name = standard_skill_name(event_type)
    skill_directory = output_root / skill_name
    image_directory = skill_directory / "media" / "images"
    video_directory = skill_directory / "media" / "videos"
    image_directory.mkdir(parents=True)
    video_directory.mkdir(parents=True)

    positive_image_count, negative_image_count = balanced_counts(image_count)
    positive_video_count, negative_video_count = balanced_counts(video_count)

    positive_images = list_media_files(source_root / event_type, IMAGE_SUFFIXES)
    negative_images = list_media_files(
        source_root / (event_type + "_neg"),
        IMAGE_SUFFIXES,
    )
    positive_videos = list_media_files(
        source_root / (event_type + "2"),
        VIDEO_SUFFIXES,
    )
    negative_videos = list_media_files(
        source_root / (event_type + "2_neg"),
        VIDEO_SUFFIXES,
    )

    image_tasks = []
    image_source_mode = "image"
    if positive_images and negative_images:
        selected_positive_images = select_readable_files(
            positive_images,
            positive_image_count,
            "image",
        )
        selected_negative_images = select_readable_files(
            negative_images,
            negative_image_count,
            "image",
        )
        image_tasks.extend(
            copy_image_tasks(
                event_type,
                "positive",
                selected_positive_images,
                image_directory,
                source_root,
                0,
            )
        )
        image_tasks.extend(
            copy_image_tasks(
                event_type,
                "negative",
                selected_negative_images,
                image_directory,
                source_root,
                positive_image_count,
            )
        )
    else:
        image_source_mode = "video_frame"
        selected_positive_sources = select_readable_files(
            positive_videos,
            positive_image_count,
            "video",
        )
        selected_negative_sources = select_readable_files(
            negative_videos,
            negative_image_count,
            "video",
        )
        image_tasks.extend(
            extract_image_tasks(
                event_type,
                "positive",
                selected_positive_sources,
                image_directory,
                source_root,
                0,
            )
        )
        image_tasks.extend(
            extract_image_tasks(
                event_type,
                "negative",
                selected_negative_sources,
                image_directory,
                source_root,
                positive_image_count,
            )
        )

    selected_positive_videos = select_readable_files(
        positive_videos,
        positive_video_count,
        "video",
    )
    selected_negative_videos = select_readable_files(
        negative_videos,
        negative_video_count,
        "video",
    )
    video_tasks = []
    video_tasks.extend(
        copy_video_tasks(
            event_type,
            "positive",
            selected_positive_videos,
            video_directory,
            source_root,
            0,
        )
    )
    video_tasks.extend(
        copy_video_tasks(
            event_type,
            "negative",
            selected_negative_videos,
            video_directory,
            source_root,
            positive_video_count,
        )
    )

    tasks = image_tasks + video_tasks
    write_json(skill_directory / "explore.json", tasks)

    metadata = ANOMALY_CLASS_METADATA[event_type]
    manifest = {
        "event_type": event_type,
        "skill_name": skill_name,
        "title": metadata["title"],
        "source_description": read_source_description(source_root, event_type),
        "dataset_path": "explore.json",
        "media_root": ".",
        "image_count": len(image_tasks),
        "video_count": len(video_tasks),
        "positive_count": positive_image_count + positive_video_count,
        "negative_count": negative_image_count + negative_video_count,
        "image_source_mode": image_source_mode,
        "source_folders": {
            "positive_images": event_type,
            "negative_images": event_type + "_neg",
            "positive_videos": event_type + "2",
            "negative_videos": event_type + "2_neg",
            "description": event_type + "3",
        },
    }
    write_json(skill_directory / "manifest.json", manifest)
    return manifest


def build_datasets(source_root, output_root, image_count, video_count, force):
    if image_count < 0 or video_count < 0:
        raise ValueError("图片数和视频数不能是负数。")
    if image_count == 0 and video_count == 0:
        raise ValueError("图片数和视频数不能同时为 0。")
    if not source_root.is_dir():
        raise FileNotFoundError("原始数据目录不存在：" + str(source_root))
    if output_root.exists():
        if not force:
            raise FileExistsError(
                "输出目录已存在；如需重建，请添加 --force："
                + str(output_root)
            )
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    datasets = []
    for event_type in ANOMALY_EVENT_TYPES:
        print("正在构建：" + event_type, flush=True)
        manifest = build_event_dataset(
            source_root,
            output_root,
            event_type,
            image_count,
            video_count,
        )
        datasets.append(
            {
                "event_type": manifest["event_type"],
                "skill_name": manifest["skill_name"],
                "title": manifest["title"],
                "dataset_path": manifest["skill_name"] + "/explore.json",
                "media_root": manifest["skill_name"],
                "image_count": manifest["image_count"],
                "video_count": manifest["video_count"],
                "positive_count": manifest["positive_count"],
                "negative_count": manifest["negative_count"],
                "image_source_mode": manifest["image_source_mode"],
            }
        )

    index = {
        "source_root": str(source_root),
        "dataset_count": len(datasets),
        "image_count_per_dataset": image_count,
        "video_count_per_dataset": video_count,
        "datasets": datasets,
    }
    write_json(output_root / "INDEX.json", index)


def validate_dataset(output_root, entry, expected_image_count, expected_video_count):
    event_type = entry["event_type"]
    skill_name = entry["skill_name"]
    skill_directory = output_root / skill_name
    dataset_path = skill_directory / "explore.json"
    manifest_path = skill_directory / "manifest.json"
    if not dataset_path.is_file():
        raise FileNotFoundError("缺少数据集文件：" + str(dataset_path))
    if not manifest_path.is_file():
        raise FileNotFoundError("缺少 manifest：" + str(manifest_path))

    with open(dataset_path, "r", encoding="utf-8") as handle:
        tasks = json.load(handle)
    if not isinstance(tasks, list):
        raise ValueError("explore.json 不是数组：" + str(dataset_path))

    image_count = 0
    video_count = 0
    positive_count = 0
    negative_count = 0
    task_ids = set()
    for task in tasks:
        if task.get("event_type") != event_type:
            raise ValueError("event_type 不一致：" + str(dataset_path))
        task_id = task.get("task_id")
        if not task_id or task_id in task_ids:
            raise ValueError("task_id 缺失或重复：" + str(dataset_path))
        task_ids.add(task_id)

        answer = task.get("answer")
        if answer == POSITIVE_ANSWER:
            positive_count += 1
        elif answer == NEGATIVE_ANSWER:
            negative_count += 1
        else:
            raise ValueError("answer 不是“是”或“否”：" + str(dataset_path))

        media_path = skill_directory / str(task.get("media_path", ""))
        if not media_path.is_file() or media_path.stat().st_size == 0:
            raise FileNotFoundError("媒体文件缺失或为空：" + str(media_path))
        suffix = media_path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            image_count += 1
            if not image_is_readable(media_path):
                raise ValueError("图片不可读：" + str(media_path))
        elif suffix in VIDEO_SUFFIXES:
            video_count += 1
            if not video_is_readable(media_path):
                raise ValueError("视频不可读：" + str(media_path))
        else:
            raise ValueError("媒体后缀不受支持：" + str(media_path))

    if image_count != expected_image_count:
        raise ValueError(
            event_type
            + " 图片数量错误："
            + str(image_count)
            + " != "
            + str(expected_image_count)
        )
    if video_count != expected_video_count:
        raise ValueError(
            event_type
            + " 视频数量错误："
            + str(video_count)
            + " != "
            + str(expected_video_count)
        )
    if len(tasks) != positive_count + negative_count:
        raise ValueError(event_type + " 正负样本统计错误。")


def validate_datasets(output_root):
    index_path = output_root / "INDEX.json"
    if not index_path.is_file():
        raise FileNotFoundError("缺少总索引：" + str(index_path))
    with open(index_path, "r", encoding="utf-8") as handle:
        index = json.load(handle)

    datasets = index.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("INDEX.json 缺少 datasets 数组。")
    if len(datasets) != len(ANOMALY_EVENT_TYPES):
        raise ValueError(
            "数据集类别数错误："
            + str(len(datasets))
            + " != "
            + str(len(ANOMALY_EVENT_TYPES))
        )

    expected_image_count = int(index["image_count_per_dataset"])
    expected_video_count = int(index["video_count_per_dataset"])
    event_types = set()
    for entry in datasets:
        event_type = entry["event_type"]
        if event_type in event_types:
            raise ValueError("INDEX.json 中类别重复：" + event_type)
        event_types.add(event_type)
        validate_dataset(
            output_root,
            entry,
            expected_image_count,
            expected_video_count,
        )
    if event_types != set(ANOMALY_EVENT_TYPES):
        raise ValueError("INDEX.json 的事件类别集合与框架不一致。")
    print(
        "验证通过："
        + str(len(datasets))
        + " 个类别，每类 "
        + str(expected_image_count)
        + " 张图片、"
        + str(expected_video_count)
        + " 个视频。"
    )


def main():
    arguments = parse_arguments()
    source_root = Path(arguments.source_root).resolve()
    output_root = Path(arguments.output_root).resolve()
    if not arguments.validate_only:
        build_datasets(
            source_root,
            output_root,
            arguments.image_count,
            arguments.video_count,
            arguments.force,
        )
    validate_datasets(output_root)


if __name__ == "__main__":
    main()
