"""Executable SpatialSkillGrowth Skill: kitchen_infested_with_rats."""

WORKFLOW_ID = 'kitchen_infested_with_rats_14a547780a36'
PROBLEM_CLASS = 'kitchen_infested_with_rats'
WORKFLOW_GRAPH_SHA256 = 'cf865328b00152e9e92796676d9f222eefcd02214d8dece3cb0d55b55c4c54f2'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'kitchen_infested_with_rats_14a547780a36', 'name': 'kitchen_infested_with_rats', 'problem_class': 'kitchen_infested_with_rats', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于图像输入，利用开放词汇检测器（GroundingDINO）定位目标，并结合多模态大语言模型（MLLM）进行视觉证据推理，以判定厨房环境中是否存在老鼠异常事件。', 'exclusions': '非厨房场景（如卧室、办公室、户外等）; 非老鼠类动物（如猫、狗、昆虫等）; 非图像类型的媒体输入; 需要调用 embeddingTool 的场景', 'capability_boundary': '{"event_type": "kitchen_infested_with_rats", "required_evidence": ["通过 GroundingDINO 检测到的老鼠实例（阈值 0.3）", "MLLM 基于图像上下文对老鼠存在性的确认"], "detection_scope": "仅限厨房环境内的老鼠检测", "tool_constraints": ["禁止使用 embeddingTool", "必须使用图像工具和多模态模型收集视觉证据"]}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': "使用低阈值检测 'rat', 'mouse', 'rodent' 等目标，以捕获潜在的小目标或模糊目标作为证据。", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 kitchen_infested_with_rats 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 kitchen_infested_with_rats 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用低阈值检测 'rat', 'mouse', 'rodent' 等目标，以捕获潜在的小目标或模糊目标作为证据。", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 kitchen_infested_with_rats 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 kitchen_infested_with_rats 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 kitchen_infested_with_rats 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
