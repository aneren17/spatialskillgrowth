"""Executable SpatialSkillGrowth Skill: pipeline_leak_detector."""

WORKFLOW_ID = 'pipeline_leak_ad1b245c64fb'
PROBLEM_CLASS = 'pipeline_leak'
WORKFLOW_GRAPH_SHA256 = 'd4201b5fc8e7aa479a14c23be149b73cad724e4ee159ccd57b862e7979af1516'
DECLARED_TOOLS = ('groundingdino', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'pipeline_leak_ad1b245c64fb', 'name': 'pipeline_leak_detector', 'problem_class': 'pipeline_leak', 'required_slots': [], 'required_tools': ['groundingdino', 'python_code_sandbox', 'MLLM'], 'description': '基于视觉证据检测图像中是否发生管道泄漏异常。工作流首先利用 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，随后通过代码沙箱计算结构化证据摘要，最后由多模态大模型综合视觉特征与证据摘要，判定是否存在管道泄漏。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 pipeline_leak 类别的异常检测任务; 无法通过视觉证据直接推断泄漏状态的抽象或概念性图像', 'capability_boundary': '仅适用于输入为图像且目标为检测 pipeline_leak 的场景。检测逻辑严格依赖于 GroundingDINO 的视觉定位结果及后续的结构化证据分析，不涉及音频、文本日志或其他模态数据的融合。', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'pipeline_leak', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 pipeline_leak 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 pipeline_leak 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'pipeline_leak', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 pipeline_leak 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 pipeline_leak 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 pipeline_leak 异常事件。',
        depends_on=['groundingdino_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
