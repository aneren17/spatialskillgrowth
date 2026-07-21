"""Executable SpatialSkillGrowth Skill: equipment_rust_detector."""

WORKFLOW_ID = 'equipment_rust_68bfa4a01e72'
PROBLEM_CLASS = 'equipment_rust'
WORKFLOW_GRAPH_SHA256 = '9653eba3600aa25d995cdf55e33a03e9f0d4458c4425935736ca294e3e1ce4d5'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'equipment_rust_68bfa4a01e72', 'name': 'equipment_rust_detector', 'problem_class': 'equipment_rust', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '针对静态图像输入，检测工业设备或金属构件表面是否存在生锈异常。工作流首先利用 GroundingDINO 以 0.3 的置信度阈值定位潜在锈蚀区域，随后通过 UniDepth 估算目标深度以辅助空间理解，最后由多模态大语言模型（MLLM）综合视觉证据判断是否发生设备生锈事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非设备类物体（如自然景观、生物体、非金属材质表面）的锈蚀或变色检测; 需要实时视频流分析或动态行为识别的场景', 'capability_boundary': '{"supported_event_type": "equipment_rust", "supported_media_type": "image", "detection_logic": "基于开放词汇检测定位、深度估计辅助及多模态推理的综合判断", "constraint": "严格限制于静态图像中的设备生锈检测，不泛化至其他类型的设备故障或非设备类锈蚀"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'equipment_rust', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 equipment_rust 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 equipment_rust 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'equipment_rust', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 equipment_rust 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 equipment_rust 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 equipment_rust 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
