"""Executable SpatialSkillGrowth Skill: explosion_detection_workflow."""

WORKFLOW_ID = 'explosion_ca756c4f9788'
PROBLEM_CLASS = 'explosion'
WORKFLOW_GRAPH_SHA256 = 'd7c6284963c79053d5dcbec03b2d4d159e5b9ff9b6376648a3c951e10c463713'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'explosion_ca756c4f9788', 'name': 'explosion_detection_workflow', 'problem_class': 'explosion', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '基于开放词汇目标检测、深度估计及多模态大模型推理的爆炸事件检测工作流。该流程首先使用 GroundingDINO 以 0.3 阈值检测潜在爆炸相关视觉特征，随后通过 UniDepth 估计目标深度信息，最后由多模态大模型综合视觉证据判断是否发生爆炸异常。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 explosion 类别的异常检测任务; 不包含爆炸相关视觉特征（如火焰、烟雾、冲击波、碎片等）的静态背景图像', 'capability_boundary': '{"required_tools": ["groundingdino", "unidepth", "MLLM"], "input_constraints": {"media_type": "image", "event_type": "explosion"}, "detection_logic": "依赖 GroundingDINO 的开放词汇检测能力定位目标，结合 UniDepth 的空间深度信息，由 MLLM 进行最终语义判定。不支持非图像输入，不执行 embedding 操作。"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'explosion', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 explosion 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 explosion 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'explosion', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 explosion 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 explosion 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 explosion 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
