"""Executable SpatialSkillGrowth Skill: tank_body_landing_detector."""

WORKFLOW_ID = 'tank_body_landing_a798073ef370'
PROBLEM_CLASS = 'tank_body_landing'
WORKFLOW_GRAPH_SHA256 = '2566280318cb1ef183728c732a6decf3da6b3f534fe3c4ccc28c4c498be0062b'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'tank_body_landing_a798073ef370', 'name': 'tank_body_landing_detector', 'problem_class': 'tank_body_landing', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '基于视觉证据检测罐体（tank_body）是否发生落地异常。工作流首先利用开放词汇检测器定位罐体，随后通过单目深度估计分析其空间位置，最后结合多模态大模型综合判断罐体是否接触地面或处于非正常着陆状态。', 'exclusions': '非图像类型的媒体输入; 未包含罐体（tank_body）目标的场景; 需要语义嵌入（embedding）分析的任务; 其他类型的异常事件检测', 'capability_boundary': '{"event_type": "tank_body_landing", "media_type": "image", "required_evidence": ["罐体目标的视觉检测框", "罐体目标的深度估计信息"], "constraints": ["必须保留 tank_body_landing 事件类型", "禁止调用 embeddingTool", "仅针对罐体落地这一特定异常类别，不泛化至其他异常"]}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'tank_body_landing', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 tank_body_landing 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 tank_body_landing 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'tank_body_landing', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 tank_body_landing 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 tank_body_landing 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 tank_body_landing 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
