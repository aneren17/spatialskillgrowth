import os
import base64
import requests
from langchain_core.tools import tool


@tool
def crop_detections(file: str, detections: str, folder: str, score: str = "0.5", className: str = "") -> str:
    """
    根据检测框对图像进行裁剪。输入原始图像和检测结果，返回裁剪后的图像列表。

    detections 参数格式（必须是 JSON 字符串）:
      {"detections": [{"class_name": "person", "bbox": [x1,y1,x2,y2], "score": 0.9}]}
      或直接传入数组: [{"class_name": "person", "bbox": [x1,y1,x2,y2], "score": 0.9}]

    注意: bbox 是 [左上x, 左上y, 右下x, 右下y] 格式的像素坐标。

    category: 数值参数类

    Args:
        file: 原始图像路径（支持本地路径、URL 或 Base64）
        detections: 检测框 JSON 字符串，格式见上方示例
        score: 置信度阈值，默认 0.5。低于此值的检测框会被过滤
        folder: 输出文件夹路径（按类别分目录存放裁剪结果）
        className: 可选，只裁剪特定类别的检测框。留空则裁剪全部

    """
    # ================= 修改逻辑开始 =================
    processed_file = file
    
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"
    # ================= 修改逻辑结束 =================

    url = "http://172.16.0.33:9418/api/v1/picCut"
    payload = {
        "file": processed_file,
        "detections": detections,
        "score": score,
        "folder": folder,
        "className": className
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing crop_detections: {str(e)}"


@tool
def picRelativeCut(file: str, folder: str, detections: str, score: str = "0.5",  className: str = "") -> str:
    """
    基于检测框做相对位置裁剪。与 crop_detections 不同，此工具会保留检测框之间的相对空间关系。

    detections 参数格式（必须是 JSON 字符串）:
      {"detections": [{"class_name": "person", "bbox": [x1,y1,x2,y2], "score": 0.9}]}
      或直接传入数组: [{"class_name": "person", "bbox": [x1,y1,x2,y2], "score": 0.9}]

    ⚠️ bbox 坐标必须是 0~1 之间的小数（归一化坐标）！
       例如: [0.12, 0.34, 0.56, 0.78]
       像素坐标需先除以图片宽高转换为归一化坐标再传入。

    category: 数值参数类

    Args:
        file: 原始图像路径（支持本地路径、URL 或 Base64）
        detections: 检测框 JSON 字符串，格式见上方示例
        score: 置信度阈值，默认 0.5。低于此值的检测框会被过滤
        folder: 输出文件夹路径（按类别分目录存放裁剪结果）
        className: 可选，只裁剪特定类别的检测框。留空则裁剪全部

    """
    # ================= 修改逻辑开始 =================
    processed_file = file
    
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"
    # ================= 修改逻辑结束 =================

    url = "http://172.16.0.33:9418/api/v1/picRelativeCut"
    payload = {
        "file": processed_file,
        "detections": detections,
        "score": score,
        "folder": folder,
        "className": className
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing picRelativeCut: {str(e)}"