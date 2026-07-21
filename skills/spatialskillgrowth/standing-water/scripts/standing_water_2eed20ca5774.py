"""Executable SpatialSkillGrowth Skill: standing_water_detector."""

WORKFLOW_ID = 'standing_water_2eed20ca5774'
PROBLEM_CLASS = 'standing_water'
WORKFLOW_GRAPH_SHA256 = 'c11f0011c0699f4d967cc90a8462a40ce6a70ccd7fcca054e5bee3798361b73d'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'standing_water_2eed20ca5774', 'name': 'standing_water_detector', 'problem_class': 'standing_water', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '基于多模态视觉证据检测图像中是否存在积水异常。工作流首先利用开放词汇检测模型定位潜在积水区域，随后通过深度估计分析其空间形态，最终由多模态大模型综合视觉特征判定是否构成积水事件。', 'exclusions': '非图像类型的媒体输入; 需要语义嵌入处理的场景; 非积水类别的异常检测任务; 缺乏明确视觉边界的模糊积水疑似区域', 'capability_boundary': '{"required_evidence": ["积水区域的边界框定位", "目标区域的深度信息", "多模态模型对积水特征的最终确认"], "detection_scope": "仅针对 event_type 为 standing_water 的图像输入进行异常判定", "tool_constraints": "必须使用 groundingdino 进行初始检测，unidepth 进行深度估计，MLLM 进行最终推理"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'standing_water', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 standing_water 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 standing_water 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'standing_water', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 standing_water 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 standing_water 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 standing_water 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
