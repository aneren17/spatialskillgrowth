"""Executable SpatialSkillGrowth Skill: egress_blocked_detector."""

WORKFLOW_ID = 'egress_blocked_661077834e2a'
PROBLEM_CLASS = 'egress_blocked'
WORKFLOW_GRAPH_SHA256 = '8b3b80d7470944b19dffce3b9545735a6f781c7553628f3f3d81a6b3a47bd9ea'
DECLARED_TOOLS = ('groundingdino', 'paddleOcrTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'egress_blocked_661077834e2a', 'name': 'egress_blocked_detector', 'problem_class': 'egress_blocked', 'required_slots': [], 'required_tools': ['groundingdino', 'paddleOcrTool', 'unidepth', 'MLLM'], 'description': '基于多模态视觉证据检测图像中的安全出口遮挡异常。通过开放词汇检测定位潜在障碍物，结合OCR识别出口标识文字，并利用深度估计分析空间遮挡关系，最终由多模态大模型综合判断是否发生出口堵塞。', 'exclusions': '非图像类型的媒体输入; 未包含安全出口或疏散通道场景的图像; 无法通过视觉手段识别出口标识或障碍物深度的模糊图像', 'capability_boundary': '{"required_evidence": ["通过 groundingdino 检测到的潜在障碍物边界框", "通过 paddleocr 识别的出口相关文字信息", "通过 unidepth 估计的障碍物与出口区域的深度关系"], "detection_scope": "仅针对已确定类别为 egress_blocked 的安全出口遮挡事件进行检测，不扩展至其他类型的异常事件", "input_constraint": "仅支持图像输入，禁止调用 embedding 工具"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': '使用低阈值检测潜在遮挡物（如箱子、家具），确保不遗漏低置信度目标', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 egress_blocked 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 egress_blocked 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'paddleocrtool_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': '使用低阈值检测潜在遮挡物（如箱子、家具），确保不遗漏低置信度目标', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 egress_blocked 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 egress_blocked 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 egress_blocked 异常事件。',
        depends_on=['groundingdino_0', 'paddleocrtool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
