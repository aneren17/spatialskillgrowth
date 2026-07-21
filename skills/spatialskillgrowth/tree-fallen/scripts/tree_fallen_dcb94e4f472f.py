"""Executable SpatialSkillGrowth Skill: tree_fallen_detector."""

WORKFLOW_ID = 'tree_fallen_dcb94e4f472f'
PROBLEM_CLASS = 'tree_fallen'
WORKFLOW_GRAPH_SHA256 = '63967ccf970331ae0bbca2de0088ab7bb5b7715fb4a5bb0fb601d0d7f2444c6e'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'tree_fallen_dcb94e4f472f', 'name': 'tree_fallen_detector', 'problem_class': 'tree_fallen', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '基于图像输入，利用开放词汇目标检测与深度估计技术，验证是否存在‘树木倒伏’异常事件。该工作流首先通过 groundingdino 定位树木目标，随后使用 unidepth 评估其空间深度信息，最后结合多模态大模型综合视觉证据进行判定。', 'exclusions': '非图像类型的媒体输入（如视频流、纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非‘树木倒伏’类别的其他异常事件（如火灾、积水、车辆故障等）; 未提供原始图像像素数据的场景', 'capability_boundary': '{"required_evidence": ["通过 groundingdino 检测到的树木目标及其边界框", "通过 unidepth 生成的对应目标深度图或深度估计值", "多模态模型基于上述视觉特征输出的逻辑判断依据"], "constraints": ["仅针对 event_type 为 \'tree_fallen\' 的场景生效", "必须保留 groundingdino 的 0.3 检测阈值设定", "不得抽象或替换‘树木’这一具体检测对象，因为工具图中无通用物体槽位", "最终输出必须为二分类结果（是/否），不包含概率值或置信度分数"]}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'tree_fallen', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 tree_fallen 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'tree_fallen', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 tree_fallen 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 tree_fallen 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
