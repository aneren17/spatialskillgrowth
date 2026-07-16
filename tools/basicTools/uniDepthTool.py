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
def unidepth(
    detections: str,
    file: str,
    filename: str,
) -> str:
    """
    Estimate the metric depth of detected objects using UniDepthV2.

    This tool accepts object detection results and estimates the median depth
    in meters inside each bounding box.

    detections MUST be a JSON string list. Each item must contain:
        cls: Object class name.
        box: Bounding box in [xmin, ymin, xmax, ymax] format.
        score: Detection confidence score.

    Example:
        '[{"cls":"person","box":[120,80,460,690],"score":0.92}]'

    The detections returned by GroundingDINO can be passed directly to this
    tool after converting them to a JSON string.

    category: 空间度量类

    Args:
        detections: JSON string containing detection boxes, classes and scores.
        file: Input image URL, local image path, file identifier, or Base64
            encoded image.
        filename: Input image filename.

    Returns:
        A JSON string containing each detected object's class, bounding box,
        confidence score and estimated depth in meters.
    """
    try:
        parsed_detections = json.loads(detections)

        if isinstance(parsed_detections, dict):
            parsed_detections = [parsed_detections]

        if not isinstance(parsed_detections, list):
            raise ValueError(
                "detections must be a JSON list"
            )

        processed_file = process_file(file)

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Invalid detections or input image: {exc}"
                ),
            },
            ensure_ascii=False,
        )

    url = "http://172.16.0.33:9418/api/v1/unidepth"

    payload = {
        "detections": json.dumps(
            parsed_detections,
            ensure_ascii=False,
        ),
        "file": processed_file,
        "filename": filename,
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
        depth_results = (
            data.get("originalResponse", [])
            if isinstance(data, dict)
            else []
        )

        return json.dumps(
            {
                "status": "success",
                "detections": depth_results,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Error executing UniDepth: {exc}"
                ),
            },
            ensure_ascii=False,
        )