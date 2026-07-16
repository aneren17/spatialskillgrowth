import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from mdconvert import MarkdownConverter

from model.DeepSeekFactory.DeepSeekFactory import get_llm

md_converter = MarkdownConverter()

class TextInspectorInput(BaseModel):
    file_path: str = Field(
        description="The path to the file you want to read as text. Must be a '.something' file, like '.pdf'. If it is an image, use the visualizer tool instead! DO NOT USE THIS TOOL FOR A WEBPAGE: use the search tool instead!"
    )
    question: Optional[str] = Field(
        default=None,
        description="[Optional]: Your question, as a natural language sentence. Provide as much context as possible. Do not pass this parameter if you just want to directly return the content of the file."
    )

@tool("inspect_file_as_text", args_schema=TextInspectorInput)
def inspect_file_as_text(file_path: str, question: Optional[str] = None) -> str:
    """You cannot load files yourself: instead call this tool to read a file as markdown text and ask questions about it. This tool handles the following file extensions:[".html", ".htm", ".xlsx", ".pptx", ".wav", ".mp3", ".flac", ".pdf", ".docx"], and all other types of text files. IT DOES NOT HANDLE IMAGES.

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
    prompt = (
        f"You will have to write a short caption for this file, then answer this question: {question}\n\n"
        f"Here is the complete file:\n### {title}\n\n"
        f"{result.text_content[:70000]}\n\n"
        f"Now answer the question below. Use these three headings: '1. Short answer', '2. Extremely detailed answer', '3. Additional Context on the document and question asked'.\n"
        f"Question: {question}"
    )
    
    # 6. 调用 LLM 并返回结果
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Error analyzing file with LLM: {str(e)}"