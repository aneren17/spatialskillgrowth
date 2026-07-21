"""Executable SpatialSkillGrowth Skill: container_dropped_detector."""

WORKFLOW_ID = 'container_dropped_c47dbc69142b'
PROBLEM_CLASS = 'container_dropped'
WORKFLOW_GRAPH_SHA256 = '9c4857629e5e210e26954c118836de93435abdde1f457aa90ff7d955fa69e6d9'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'container_dropped_c47dbc69142b', 'name': 'container_dropped_detector', 'problem_class': 'container_dropped', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大模型（MLLM）分析输入图像，检测是否存在集装箱掉落或坠落的异常事件。该工作流通过视觉证据判断集装箱是否脱离正常堆叠或运输状态并发生非受控坠落，适用于港口、堆场等场景的静态图像异常检测。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征提取的任务; 非 container_dropped 类别的其他异常事件（如集装箱倾斜、破损或火灾）; 需要实时视频流处理或时序分析的动态场景', 'capability_boundary': '{"supported_media": ["image"], "event_type": "container_dropped", "evidence_source": "visual_analysis", "tool_dependency": ["MLLM"], "output_format": "binary_classification"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 container_dropped 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。; 给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 container_dropped 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 container_dropped 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 container_dropped 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。; 给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 container_dropped 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
