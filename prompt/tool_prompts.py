"""基础工具内部使用的中文 LLM 提示词。"""

TEXT_INSPECTOR_QUESTION_PROMPT = """请先为文件写一句简短概述，再回答用户问题。

以下是完整文件内容：
### {title}

{content}

请使用以下三个标题回答：
1. 简短回答
2. 详细回答
3. 文件与问题的补充背景

用户问题：{question}
"""
