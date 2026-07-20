"""Banner OCR 辅助检测的人工脚本示例。"""

WORKFLOW_ID = "banner-ocr-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool", "paddleOcrTool", "MLLM")
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_ocr_example",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合横幅文字清晰可见的画面；先取得主判断，再读取文字并交给 MLLM 辅助查看。",
    "exclusions": "不适用于 banner 以外类别；文字完全不可见时 OCR 不能提供有效补充。",
    "capability_boundary": (
        "embeddingTool 必须成功并返回是或否；OCR 和 MLLM 都是可选证据，"
        "任一步失败时仍返回 embeddingTool 的判断。"
    ),
    "steps": [
        {
            "tool_name": "embeddingTool",
            "args": {
                "file_path": "$media",
                "event_type": "$slot.event_type",
            },
            "step_id": "embedding",
            "depends_on": [],
            "purpose": "取得 banner 主判断和阈值。",
        },
        {
            "tool_name": "paddleOcrTool",
            "args": {
                "file": "$image",
                "filename": "$filename",
            },
            "step_id": "ocr",
            "depends_on": [],
            "purpose": "读取画面中的横幅文字。",
        },
        {
            "tool_name": "MLLM",
            "args": {
                "file": "$evidence_image",
                "filename": "$filename",
                "query": "$question\n$evidence",
                "tool": "qwen36Tool",
            },
            "step_id": "review",
            "depends_on": ["embedding", "ocr"],
            "purpose": "结合画面和 OCR 文字补充说明。",
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
        purpose="取得 banner 主判断和阈值。",
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
        purpose="读取画面中的横幅文字。",
        depends_on=[],
    )

    evidence_image = runtime.evidence_image()
    runtime.call(
        "MLLM",
        {
            "file": evidence_image,
            "filename": runtime.filename(evidence_image),
            "query": question + "\n" + runtime.evidence_text(),
            "tool": "qwen36Tool",
        },
        step_id="review",
        purpose="结合画面和 OCR 文字补充说明。",
        depends_on=["embedding", "ocr"],
    )

    return runtime.finish(embedding)
