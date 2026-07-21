"""Executable SpatialSkillGrowth Skill: fire_hydrant_leakage_detector."""

WORKFLOW_ID = 'fire_hydrant_leakage_06ff05f588ac'
PROBLEM_CLASS = 'fire_hydrant_leakage'
WORKFLOW_GRAPH_SHA256 = 'fe8ac177b1a21bca5d905eadfebdbcc3abbac76918762cee5bf377abada4ce20'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_hydrant_leakage_06ff05f588ac', 'name': 'fire_hydrant_leakage_detector', 'problem_class': 'fire_hydrant_leakage', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '针对输入图像执行消防栓泄漏异常检测。工作流首先利用 GroundingDINO 以 0.3 的开放词汇检测阈值定位消防栓目标，随后通过 UniDepth 估计目标的深度信息以辅助空间理解，最后结合多模态大语言模型（MLLM）分析视觉证据，判断是否存在消防栓泄漏现象。', 'exclusions': '非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 进行特征嵌入的场景; 非 fire_hydrant_leakage 类别的其他异常事件检测; 需要重新分类或改写事件类别的任务', 'capability_boundary': '{"required_tools": ["groundingdino", "unidepth", "MLLM"], "input_modality": "image", "event_type": "fire_hydrant_leakage", "detection_threshold": 0.3, "output_format": "binary (是/否)", "constraints": ["禁止使用 embeddingTool", "必须保留 fire_hydrant_leakage 事件类型不变", "仅基于视觉证据进行判断"]}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'fire_hydrant_leakage', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 fire_hydrant_leakage 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'fire_hydrant_leakage', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 fire_hydrant_leakage 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire_hydrant_leakage 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
