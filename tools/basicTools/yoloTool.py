import os
import base64
import requests
from langchain_core.tools import tool

@tool
def yoloTool(file: str, filename: str, threshold: float = 0.5) -> str:
    """
    通用目标检测工具（YOLO + COCO 预训练权重）。支持检测 80 类常见物体。
    传入图像 URL、本地路径或 Base64 字符串，返回带检测框的图片的url、检测到的目标类别、置信度和边界框坐标。

    可检测类别：person, bicycle, car, motorcycle, airplane, bus, train, truck,
    boat, traffic light, fire hydrant, stop sign, parking meter, bench, bird, cat,
    dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella,
    handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat,
    baseball glove, skateboard, surfboard, tennis racket, bottle, wine glass, cup,
    fork, knife, spoon, bowl, banana, apple, sandwich, orange, broccoli, carrot,
    hot dog, pizza, donut, cake, chair, couch, potted plant, bed, dining table,
    toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven,
    toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier,
    toothbrush 等 80 类。

    适用场景：检测图中是否有特定物体（人、车、动物、家具、食物等），获取其位置和数量。

    category: 固定检测类

    Args:
        file: 图像路径、URL 或 Base64 编码字符串。
        filename: 图像文件名。
        threshold: 检测置信度阈值（0.0～1.0），默认 0.5；值越高，结果越少但置信度越高。
    """
    processed_file = file

    # 判断是否为本地存在的文件路径
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"

    url = "http://172.16.0.33:9418/api/v1/yolo"
    payload = {
        "file": processed_file,
        "filename": filename,
        "tool": "yoloTool",
        "threshold": threshold,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing yoloTool: {str(e)}"
