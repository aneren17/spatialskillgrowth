"""Executable SpatialSkillGrowth Skill: vehicle_illegal_parking_detector."""

WORKFLOW_ID = 'vehicle_illegal_parking_1310756365ce'
PROBLEM_CLASS = 'vehicle_illegal_parking'
WORKFLOW_GRAPH_SHA256 = '6947b4d1d69fb1d891297ef94a80dd72c6587c3d381790e042d9224f40c55599'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'vehicle_illegal_parking_1310756365ce', 'name': 'vehicle_illegal_parking_detector', 'problem_class': 'vehicle_illegal_parking', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'MLLM'], 'description': '基于图像输入，通过 OCR 提取场景文字信息与 YOLO 检测车辆目标，结合多模态大模型综合判断是否存在车辆违停异常事件。', 'exclusions': '非图像类型的媒体输入（如视频流、纯文本描述）; 需要调用 embedding 工具的场景; 非 vehicle_illegal_parking 类别的其他异常检测任务; 无法通过 OCR 或 YOLO 获取有效视觉证据的模糊或遮挡严重图像', 'capability_boundary': '{"required_evidence": ["paddleOcrTool 输出的可见文字内容", "yoloTool 输出的车辆检测框及置信度（阈值 0.5）"], "event_type": "vehicle_illegal_parking", "media_type": "image", "decision_output": "binary (是/否)"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 vehicle_illegal_parking 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 vehicle_illegal_parking 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0']}]}


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

    # 依据图像证据判断 vehicle_illegal_parking 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 vehicle_illegal_parking 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 vehicle_illegal_parking 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
