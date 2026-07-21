"""Executable SpatialSkillGrowth Skill: fire_door_unclosed_detector."""

WORKFLOW_ID = 'fire_door_unclosed_1c1aea5e038d'
PROBLEM_CLASS = 'fire_door_unclosed'
WORKFLOW_GRAPH_SHA256 = '63dac157aec8894ed6e0d5fe33760681de178efb9866f1a6bdb977b92b385c29'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_door_unclosed_1c1aea5e038d', 'name': 'fire_door_unclosed_detector', 'problem_class': 'fire_door_unclosed', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于视觉证据检测消防门是否处于未关闭状态。工作流程首先使用开放词汇检测模型（GroundingDINO）定位消防门及其状态特征，随后结合多模态大语言模型（MLLM）分析图像上下文，综合判断是否存在消防门未关闭的异常事件。', 'exclusions': '非图像类型的媒体输入; 图像中未包含消防门主体或其状态无法被视觉证据明确识别的场景; 需要调用 embeddingTool 进行特征提取的任务; 涉及其他类型异常事件（如火灾、入侵等）的检测需求', 'capability_boundary': '{"event_type": "fire_door_unclosed", "media_type": "image", "required_evidence": ["通过 GroundingDINO 检测到的消防门实例及其边界框", "多模态模型基于视觉上下文对门状态（开启/关闭）的语义判断"], "constraints": ["仅支持静态图像输入", "检测阈值固定为 0.5", "最终输出仅为二元判断（是/否）", "不执行物体名称的运行时替换，严格限定于消防门类别"]}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': "使用中等阈值检测'fire door'和'door frame'以获取结构化边界框证据", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.5, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.5 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fire_door_unclosed 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 fire_door_unclosed 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.5 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用中等阈值检测'fire door'和'door frame'以获取结构化边界框证据", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.5, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.5 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 fire_door_unclosed 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fire_door_unclosed 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire_door_unclosed 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
