import os
import base64
import json
import requests
from langchain_core.tools import tool

@tool
def sam3(query: str, file: str, filename: str, threshold: float = 0.6, tool: str = "sam3Tool") -> str:
    """
    使用 SAM 对图像进行分割。输入简短查询词、图像 URL/本地路径/Base64 字符串、文件名
    和分割阈值，返回绘制掩码的结果图 URL，以及 [xmin, ymin, xmax, ymax] 格式的目标边界框。

    受模型接口限制，query 必须是 1～3 个英文单词，不能使用句子、长短语或中文。需要长句描述
    的目标应拆成多个英文短语并分别调用。
       ✅ "equation", "red car", "person"
       ❌ "Find the mathematical equation in this image"
       ❌ "找出图中的数学公式"

    threshold：具体物体（如 car、person）建议 0.6～0.8，抽象目标（如 text）建议 0.5。

    category: 世界模型/检索类

    Args:
        tool: SAM 模型标识，必须为 sam3Tool。
        query: 仅限 1～3 个英文单词，不能使用句子或中文。
        file: 输入图像 URL、本地路径或 Base64 编码字符串。
        filename: 输入图像文件名。
        threshold: 分割阈值；具体目标使用较高值，抽象目标使用较低值。

    Returns:
        包含结果图 URL、检测边界框和置信度的字符串。
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
