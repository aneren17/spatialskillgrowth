"""Executable SpatialSkillGrowth Skill: roadside_booths_detector."""

WORKFLOW_ID = 'roadside_booths_45718f0e4667'
PROBLEM_CLASS = 'roadside_booths'
WORKFLOW_GRAPH_SHA256 = '9e06435f5d4b03faa40379ed9460113b891f789482167e5cd4365fa051f2c741'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'roadside_booths_45718f0e4667', 'name': 'roadside_booths_detector', 'problem_class': 'roadside_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'MLLM'], 'description': '基于图像输入，通过 OCR 文本识别与目标检测（YOLO）收集视觉证据，利用多模态大模型判断是否存在占道经营（roadside_booths）异常事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他非 roadside_booths 类别的异常事件检测; 未包含可见文字或特定目标结构的纯背景图像', 'capability_boundary': '{"required_tools": ["paddleOcrTool", "yoloTool", "MLLM"], "evidence_requirements": ["通过 paddleOcrTool 获取图像中的可见文字信息", "通过 yoloTool 以 0.5 阈值检测相关目标物体", "结合上述视觉证据由 MLLM 进行综合逻辑判断"], "output_format": "布尔值（是/否）", "constraints": "严格限定于 roadside_booths 事件类型，不泛化至其他占道或经营类异常"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 roadside_booths 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 roadside_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 依据图像证据判断 roadside_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 roadside_booths 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 roadside_booths 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
