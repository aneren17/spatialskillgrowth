"""Banner OCR 辅助检测的人工脚本示例。"""

WORKFLOW_ID = "banner-ocr-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("paddleOcrTool", "MLLM")
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_ocr_example",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合横幅文字清晰可见的图片或视频抽样帧；先读取文字，再由 MLLM 形成判断。",
    "exclusions": "不适用于 banner 以外类别；文字完全不可见时 OCR 不能提供有效补充。",
    "capability_boundary": (
        "不调用 embeddingTool；OCR 和 MLLM 必须成功，最终判断来自 MLLM。"
    ),
    "steps": [
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
            "depends_on": ["ocr"],
            "purpose": "结合画面和 OCR 文字形成是或否判断。",
        },
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
    ocr = runtime.call(
        "paddleOcrTool",
        {
            "file": runtime.image_path(),
            "filename": runtime.filename(),
        },
        step_id="ocr",
        purpose="读取画面中的横幅文字。",
        depends_on=[],
    )
    runtime.require(ocr, "ocr")

    evidence_image = runtime.evidence_image()
    review = runtime.call(
        "MLLM",
        {
            "file": evidence_image,
            "filename": runtime.filename(evidence_image),
            "query": question + "\n" + runtime.evidence_text(),
            "tool": "qwen36Tool",
        },
        step_id="review",
        purpose="结合画面和 OCR 文字形成是或否判断。",
        depends_on=["ocr"],
    )
    runtime.require(review, "review")

    return runtime.finish(review)
