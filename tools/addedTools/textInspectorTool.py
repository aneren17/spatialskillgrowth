import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from mdconvert import MarkdownConverter

from model.DeepSeekFactory.DeepSeekFactory import get_llm
from prompt.tool_prompts import TEXT_INSPECTOR_QUESTION_PROMPT

md_converter = MarkdownConverter()

class TextInspectorInput(BaseModel):
    file_path: str = Field(
        description="要读取为文本的文件路径，例如 .pdf 文件。图像应使用视觉工具，网页应使用搜索或网页访问工具。"
    )
    question: Optional[str] = Field(
        default=None,
        description="可选的自然语言问题，请尽量提供完整上下文；如果只需返回文件内容，则不要传入该参数。"
    )

@tool("inspect_file_as_text", args_schema=TextInspectorInput)
def inspect_file_as_text(file_path: str, question: Optional[str] = None) -> str:
    """将文件读取为 Markdown 文本，并可针对文件内容回答问题。支持 .html、.htm、.xlsx、
    .pptx、.wav、.mp3、.flac、.pdf、.docx 及其他文本文件，不支持图像。

    category: 固定检测类

    """
    
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        return "Error: File not found: " + file_path
        
    # 2. 拦截图片（返回字符串让 Agent 自己反思，而不是抛出异常让程序崩溃）
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return "Error: Cannot use inspect_file_as_text tool with images: use visualizer instead!"

    # 3. 解析文件
    try:
        result = md_converter.convert(file_path)
    except Exception as e:
        return f"Error converting file: {str(e)}"

    if result is None or not result.text_content:
        return "Error: Get empty content from file: " + file_path
    
    # 4. 如果是 zip 或者没有提问，直接返回解析后的前 70000 字符文本
    if ".zip" in file_path.lower() or not question:
        return result.text_content[:70000]
    
    # 5. 如果有 question，使用本地 LLM 进一步分析
    # 初始化你的本地 Qwen 模型
    llm = get_llm()
    
    # 组装原代码中设计的 prompt (去掉 hardcode 的 initial_exam_mode，保留主体逻辑)
    title = getattr(result, "title", "Unknown Document")
    prompt = TEXT_INSPECTOR_QUESTION_PROMPT.format(
        title=title,
        content=result.text_content[:70000],
        question=question,
    )
    
    # 6. 调用 LLM 并返回结果
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Error analyzing file with LLM: {str(e)}"
