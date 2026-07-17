"""人工维护的 Banner 异常检测 Skill 脚本。"""

WORKFLOW_ID = "banner-human-review-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool", "paddleOcrTool", "MLLM")
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_human_review",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "answer_types": ["bool"],
    "description": "先取得 banner 的 embedding 判断，再用 OCR 和 MLLM 补充可审计视觉证据。",
    "exclusions": "不适用于 banner 以外的事件类别；辅助工具不能替代 embedding 的异常判断和阈值。",
    "capability_boundary": "embedding 为强制主判断；OCR 与 MLLM 失败时降级返回 embedding 结论。",
    "steps": [
        {
            "tool_name": "embeddingTool",
            "args": {
                "file_path": "$media",
                "event_type": "$slot.event_type",
            },
            "step_id": "embedding",
            "depends_on": [],
            "purpose": "取得 banner 异常判断和判定阈值。",
        },
        {
            "tool_name": "paddleOcrTool",
            "args": {
                "file": "$image",
                "filename": "$filename",
            },
            "step_id": "ocr",
            "depends_on": [],
            "purpose": "提取横幅区域中的可见文字。",
        },
        {
            "tool_name": "MLLM",
            "args": {
                "file": "$evidence_image",
                "filename": "$filename",
                "query": "$question",
                "tool": "qwen36Tool",
            },
            "step_id": "visual-review",
            "depends_on": ["embedding", "ocr"],
            "purpose": "补充 Banner 视觉审阅证据。",
        },
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
    embedding = runtime.call(
        "embeddingTool",
        {
            "file_path": runtime.media_path(),
            "event_type": event_type,
        },
        step_id="embedding",
        purpose="取得 banner 异常判断和判定阈值。",
        depends_on=[],
    )
    runtime.require(embedding, "embedding")

    runtime.call(
        "paddleOcrTool",
        {
            "file": runtime.image_path(),
            "filename": runtime.filename(),
        },
        step_id="ocr",
        purpose="提取横幅区域中的可见文字。",
        depends_on=[],
    )

    runtime.call(
        "MLLM",
        {
            "file": runtime.evidence_image(),
            "filename": runtime.filename(),
            "query": question,
            "tool": "qwen36Tool",
        },
        step_id="visual-review",
        purpose="补充 Banner 视觉审阅证据。",
        depends_on=["embedding", "ocr"],
    )

    return runtime.finish(embedding)
