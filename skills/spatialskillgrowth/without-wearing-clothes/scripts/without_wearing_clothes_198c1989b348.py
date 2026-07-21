"""Executable SpatialSkillGrowth Skill: without_wearing_clothes_detector."""

WORKFLOW_ID = 'without_wearing_clothes_198c1989b348'
PROBLEM_CLASS = 'without_wearing_clothes'
WORKFLOW_GRAPH_SHA256 = 'dfcf928dead03a01efa061bec94290515571623dbb5b4930fe03b29a2921649a'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'without_wearing_clothes_198c1989b348', 'name': 'without_wearing_clothes_detector', 'problem_class': 'without_wearing_clothes', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于图像输入，利用多模态大模型分析视觉证据，检测场景中是否存在人员未穿着防护服的异常行为。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 进行特征提取的场景; 涉及其他类型异常事件（如未戴安全帽、未系安全带等）的检测任务', 'capability_boundary': '{"supported_event_type": "without_wearing_clothes", "supported_media_type": "image", "evidence_source": "visual_features_via_mllm", "output_format": "binary_classification"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 without_wearing_clothes 分析完整图像，并同时遵守以下推理和证据要求：分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 without_wearing_clothes 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 without_wearing_clothes 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 without_wearing_clothes 分析完整图像，并同时遵守以下推理和证据要求：分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 without_wearing_clothes 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
