"""Executable SpatialSkillGrowth Skill: track_obstacle_detector."""

WORKFLOW_ID = 'track_obstacle_87fbd3cbd1af'
PROBLEM_CLASS = 'track_obstacle'
WORKFLOW_GRAPH_SHA256 = '7ae8bb5293c511075ab945fe00dae6e0f120b2dd474e90aff557e313df3d8cd6'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'track_obstacle_87fbd3cbd1af', 'name': 'track_obstacle_detector', 'problem_class': 'track_obstacle', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于图像输入，利用 GroundingDINO 进行开放词汇目标检测，并结合多模态大语言模型（MLLM）分析视觉证据，以判定是否存在轨道异物异常事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 track_obstacle 类别的异常检测任务', 'capability_boundary': '仅针对 event_type 为 track_obstacle 且 media_type 为 image 的场景有效；依赖 GroundingDINO 0.3 阈值检测结果作为 MLLM 判断的前置证据。', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': '使用较低阈值以召回更多潜在异物候选框，即使置信度不高，也为后续 MLLM 提供审查机会。', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 track_obstacle 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': '使用较低阈值以召回更多潜在异物候选框，即使置信度不高，也为后续 MLLM 提供审查机会。', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 track_obstacle 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 track_obstacle 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
