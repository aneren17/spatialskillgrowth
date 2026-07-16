import base64
import json
import os

import requests
from langchain_core.tools import tool


def process_file(file: str) -> str:
    """本地文件转换为 Base64，URL、文件标识和 Base64 保持原样。"""
    if isinstance(file, str) and os.path.exists(file):
        with open(file, "rb") as image_file:
            return base64.b64encode(
                image_file.read()
            ).decode("utf-8")

    return file


@tool
def groundingdino(
    query: str,
    file: str,
    filename: str,
    box_threshold: float = 0.35,
    text_threshold: float = 0.25,
) -> str:
    """
    Detect objects in an image using GroundingDINO.

    The tool performs open-vocabulary object detection based on an English
    object category or referring expression. It returns the detected object
    classes, bounding boxes and confidence scores.

    query supports:
        A single category or phrase:
        ✅ "person"
        ✅ "red car"
        ✅ "person wearing a black shirt"

        A JSON string list:
        ✅ '["person", "car", "dog"]'
        ✅ '["red car", "person wearing black"]'

    Bounding boxes use the format:
        [xmin, ymin, xmax, ymax]

    category: 世界模型/检索类

    Args:
        query: English object category, referring expression, or JSON string
            list of categories.
        file: Input image URL, local image path, file identifier, or Base64
            encoded image.
        filename: Input image filename.
        box_threshold: Detection box confidence threshold. Default is 0.35.
        text_threshold: Text matching threshold. Default is 0.25.

    Returns:
        A JSON string containing the detection result image URL and detected
        objects with class names, bounding boxes and confidence scores.
    """
    try:
        processed_file = process_file(file)
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": f"Error reading input image: {exc}",
            },
            ensure_ascii=False,
        )

    url = "http://172.16.0.33:9418/api/v1/groundingDINO"

    payload = {
        "query": query,
        "file": processed_file,
        "filename": filename,
        "box_threshold": box_threshold,
        "text_threshold": text_threshold,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        result = response.json()

        data = result.get("data", {})
        detections = (
            data.get("detections", [])
            if isinstance(data, dict)
            else []
        )

        return json.dumps(
            {
                "status": "success",
                "file": result.get("file", ""),
                "detections": detections,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Error executing GroundingDINO: {exc}"
                ),
            },
            ensure_ascii=False,
        )

