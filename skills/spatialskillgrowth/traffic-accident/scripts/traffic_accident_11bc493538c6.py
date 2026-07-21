"""Executable SpatialSkillGrowth Skill: traffic_accident_detector."""

WORKFLOW_ID = 'traffic_accident_11bc493538c6'
PROBLEM_CLASS = 'traffic_accident'
WORKFLOW_GRAPH_SHA256 = 'f07c0d3b1c1ebc4849650f22cd6ddfcb194c39489b7c83ff329c850201d6ff5a'
DECLARED_TOOLS = ('yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'traffic_accident_11bc493538c6', 'name': 'traffic_accident_detector', 'problem_class': 'traffic_accident', 'required_slots': [], 'required_tools': ['yoloTool', 'unidepth', 'MLLM'], 'description': '基于视觉证据检测图像中是否发生交通事故（traffic_accident）。工作流首先利用 YOLO 工具以 0.5 的置信度阈值检测潜在目标，随后通过 UniDepth 估计检测目标的深度信息以辅助空间理解，最后结合多模态大语言模型（MLLM）综合图像特征、目标检测结果及深度证据，判断是否存在交通事故异常。', 'exclusions': '非图像类型的媒体输入（如视频、音频或纯文本）。; 需要调用 embeddingTool 进行特征提取的场景。; 非交通事故类别的异常事件检测（如火灾、入侵等，除非工具图显式支持）。; 缺乏清晰视觉证据导致无法判断事故状态的模糊图像。', 'capability_boundary': '{"input_media": "image", "event_type": "traffic_accident", "detection_logic": "YOLO目标检测(阈值0.5) -> 深度估计 -> MLLM综合判断", "output_format": "binary (是/否)", "constraints": "严格依赖工具图定义的步骤，不引入外部未定义工具；仅对交通事故类别有效。"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 traffic_accident 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

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

    # 依据图像证据判断 traffic_accident 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 traffic_accident 异常事件。',
        depends_on=['yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
