import os
import base64
import json
import requests
from langchain_core.tools import tool

@tool
def sam3(query: str, file: str, filename: str, threshold: float = 0.6, tool: str = "sam3Tool") -> str:
    """
    Perform image segmentation using SAM. You can provide concise query, the image URL, local image path, or Base64 string and its name, threshold to guide segmentation;
    the API returns an image URL with drawn masks, AND the bounding box coordinates of the detected objects in [xmin, ymin, xmax, ymax] format.

    query MUST be 1-3 English words only. Sentences, long phrases, or Chinese will cause error.(If the object you want to segment needs to be described using sentences, please modify it into a series of phrases that are called multiple times as input.)
       ✅ "equation", "red car", "person"
       ❌ "Find the mathematical equation in this image"
       ❌ "找出图中的数学公式"

    threshold: 0.6-0.8 for concrete objects (car, person), 0.5 for abstract (text, equation).

    category: 世界模型/检索类

    Args:
        tool: SAM model identifier, one of[sam3Tool]
        query: 1-3 English words ONLY — NOT a sentence, NOT Chinese(If the object you want to segment needs to be described using sentences, please modify it into a series of phrases that are called multiple times as input.)
        file: Input image URL, local image path, or Base64 encoded string
        filename: Input image filename
        threshold: Segmentation threshold. Higher for concrete objects, lower for abstract concepts.

    Returns:
        A string containing the result image URL and a list of detected bounding boxes with confidence scores.
    """
    processed_file = file
    
    # 判断是否为本地存在的文件路径
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                # 转换为 base64 并且 decode 为 utf-8 字符串
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"

    url = "http://172.16.0.33:9418/api/v1/sam"
    payload = {
        "tool": tool,
        "query": query,
        "file": processed_file,
        "filename": filename,
        "threshold": threshold
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # ================= 解析响应 =================
        res_json = response.json()
        data = res_json.get('data', {})

        # 检查是否有 file 字段且非空
        result_file = res_json.get('file', '')
        if result_file:
            detections = data.get('detections', []) if isinstance(data, dict) else []
            return json.dumps({
                "status": "success",
                "message": (
                    "Segmentation successful with bounding boxes."
                    if detections else
                    "Segmentation successful, but no bounding boxes were returned."
                ),
                "file": result_file,
                "detections": detections,
            }, ensure_ascii=False)

        # 无 file → 检查 data.originalResponse 中的具体原因
        if isinstance(data, dict):
            msg = data.get('originalResponse', '')
        else:
            msg = ''

        if '没有检测到物体' in msg or 'no mask' in msg.lower():
            return (
                "SAM3 调用成功，但未检测到可分割的物体。\n"
                "请尝试以下操作:\n"
                "  - 修改 query 为更通用/更简短的英文词（1-3 词）\n"
                "  - 降低 threshold（当前为 {}, 可尝试 0.3-0.5）\n"
                "  - 换用其他工具\n"
                "后端原始消息: {}".format(threshold, msg)
            )

        # 其他情况
        return f"API returned no result file. Raw response: {response.text[:300]}"
        
    except Exception as e:
        return f"Error executing sam3: {str(e)}"
