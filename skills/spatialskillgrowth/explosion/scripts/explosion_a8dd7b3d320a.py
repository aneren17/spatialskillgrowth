"""Executable SpatialSkillGrowth Skill: explosion_detection_workflow."""

WORKFLOW_ID = 'explosion_a8dd7b3d320a'
PROBLEM_CLASS = 'explosion'
WORKFLOW_GRAPH_SHA256 = 'b1216b1f1adcb452c3379dcda05f81becaa920dadc493b4b70998e1a4fa70975'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'explosion_a8dd7b3d320a', 'name': 'explosion_detection_workflow', 'problem_class': 'explosion', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大语言模型（MLLM）对输入图像进行视觉分析，检测是否存在爆炸异常事件。该工作流通过直接分析图像内容，识别爆炸产生的典型视觉特征（如火光、浓烟、冲击波形态等），并依据收集到的视觉证据做出最终判定。', 'exclusions': '禁止使用 embeddingTool 处理图像输入; 不适用于非图像类型的媒体数据; 不处理除 explosion 以外的其他异常事件类别; 不进行事件分类或改写，仅针对已确定的 explosion 事件进行存在性检测', 'capability_boundary': '{"event_type": "explosion", "media_type": "image", "required_evidence": "图像中可见的爆炸视觉特征", "detection_method": "MLLM 视觉分析", "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 explosion 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 explosion 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 explosion 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 explosion 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 explosion 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
