"""Executable SpatialSkillGrowth Skill: firelane_occupied_detector."""

WORKFLOW_ID = 'firelane_occupied_61ab37812c63'
PROBLEM_CLASS = 'firelane_occupied'
WORKFLOW_GRAPH_SHA256 = '59a53e4d2200725998b969da11da6b284f574ee9df242f07229a372b32e9d2e1'
DECLARED_TOOLS = ('paddleOcrTool', 'paddlePedriderDetTool', 'yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'firelane_occupied_61ab37812c63', 'name': 'firelane_occupied_detector', 'problem_class': 'firelane_occupied', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'paddlePedriderDetTool', 'yoloTool', 'unidepth', 'MLLM'], 'description': '基于图像输入，利用OCR文本识别、交通参与者检测、通用目标检测（YOLO）及深度估计（UniDepth）多模态证据，综合判断是否存在占用消防通道的异常事件。', 'exclusions': '非图像类型的媒体输入（如纯文本、音频、视频流）; 需要语义嵌入分析（embedding）的场景; 非消防通道占用类的其他异常检测任务', 'capability_boundary': '{"required_evidence": ["通过 paddleOcrTool 获取的可见文字信息", "通过 paddlePedriderDetTool 检测到的交通参与者（行人/骑行者）", "通过 yoloTool 检测到的通用目标及其边界框", "基于 yoloTool 结果由 unidepth 估计的目标深度信息"], "decision_logic": "多模态大语言模型（MLLM）融合上述四类视觉与空间证据，严格依据 firelane_occupied 定义进行二分类判断", "constraints": ["禁止调用 embedding 工具", "必须保留原始 event_type 为 firelane_occupied", "检测器限制：仅适用于静态图像输入，不支持实时视频帧序列分析"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 firelane_occupied 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 firelane_occupied 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'paddlepedriderdettool_0', 'yolotool_0', 'unidepth_0']}]}


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

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(yolotool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['yolotool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 firelane_occupied 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 firelane_occupied 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 firelane_occupied 异常事件。',
        depends_on=['paddleocrtool_0', 'paddlepedriderdettool_0', 'yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
