import os
import base64
import requests
from langchain_core.tools import tool


@tool
def asrTool(audioFile: str, audioFilename: str) -> str:
    """
    语音识别工具（Automatic Speech Recognition, SenseVoiceSmall 模型）。
    将音频文件转为文字文本。传入音频 URL、本地路径或 Base64 字符串，返回识别出的文字内容。

    适用场景：需要从音频/视频中提取语音文字时使用。
    不适用于：图像文字提取（请用 paddleOcrTool）、图像内容理解（请用 MLLM）。

    category: 固定检测类

    Args:
        audioFile: 音频文件路径、URL 或 Base64 编码字符串。
        audioFilename: 音频文件名，例如 recording.wav、speech.mp3。
    """
    processed_file = audioFile

    # 判断是否为本地存在的文件路径
    if isinstance(audioFile, str) and os.path.exists(audioFile):
        try:
            with open(audioFile, 'rb') as f:
                audio_data = f.read()
                processed_file = base64.b64encode(audio_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local audio file to base64: {str(e)}"

    url = "http://172.16.0.33:9418/api/v1/ASR"
    payload = {
        "audioFile": processed_file,
        "audioFilename": audioFilename,
        "tool": "senseVoiceSmallTool",
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing asrTool: {str(e)}"
