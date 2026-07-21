"""Executable SpatialSkillGrowth Skill: firelane_occupied_detector."""

WORKFLOW_ID = 'firelane_occupied_af8ef8146a45'
PROBLEM_CLASS = 'firelane_occupied'
WORKFLOW_GRAPH_SHA256 = '84983f12cb1825e957ad2b3f771fffe47dfaca078cd99098e0151607df286980'
DECLARED_TOOLS = ('paddleOcrTool', 'paddlePedriderDetTool', 'yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'firelane_occupied_af8ef8146a45', 'name': 'firelane_occupied_detector', 'problem_class': 'firelane_occupied', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'paddlePedriderDetTool', 'yoloTool', 'MLLM'], 'description': '基于图像输入，利用OCR文本识别、行人/骑行者检测及通用目标检测（YOLO）收集视觉证据，通过多模态大模型综合判断是否存在占用消防通道的异常事件。', 'exclusions': '非图像类型的媒体输入; 需要语义嵌入分析的场景; 非消防通道占用类的其他异常事件检测; 缺乏可见文字、交通参与者或可检测物体导致证据不足的场景', 'capability_boundary': '{"required_evidence": ["OCR识别的可见文字信息", "行人或骑行者的检测结果", "基于YOLO（阈值0.5）的目标检测结果"], "supported_media": ["image"], "fixed_event_type": "firelane_occupied", "constraints": ["禁止调用embeddingTool", "必须保留当前event_type为firelane_occupied", "最终输出仅限\'是\'或\'否\'"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 firelane_occupied 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 firelane_occupied 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'paddlepedriderdettool_0', 'yolotool_0']}]}


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

    # 检测交通参与者。
    paddlepedriderdettool_0_result = runtime.call(
        'paddlePedriderDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddlePedriderDetTool'},
        step_id='paddlepedriderdettool_0',
        purpose='检测交通参与者。',
        depends_on=[],
    )
    runtime.require(paddlepedriderdettool_0_result, 'paddlepedriderdettool_0')

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 依据图像证据判断 firelane_occupied 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 firelane_occupied 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 firelane_occupied 异常事件。',
        depends_on=['paddleocrtool_0', 'paddlepedriderdettool_0', 'yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
