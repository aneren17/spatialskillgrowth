"""Executable SpatialSkillGrowth Skill: flag_detection_workflow."""

WORKFLOW_ID = 'flag_e92162514a45'
PROBLEM_CLASS = 'flag'
WORKFLOW_GRAPH_SHA256 = 'd21f3fac600c10981f415ea634f61a4dd3e6be346601f5f9bd36f32cbfb103c7'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'flag_e92162514a45', 'name': 'flag_detection_workflow', 'problem_class': 'flag', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '本工作流用于检测输入图像中是否存在旗帜（flag）异常事件。流程首先使用 GroundingDINO 工具以 0.5 的开放词汇检测阈值识别图像中的旗帜目标，随后将检测到的视觉证据传递给多模态大语言模型（MLLM），由其依据图像内容判断是否发生旗帜异常事件。', 'exclusions': '禁止对图像输入调用 embeddingTool; 不适用于非图像类型的媒体输入; 不适用于非旗帜（flag）类别的异常检测任务', 'capability_boundary': '{"event_type": "flag", "media_type": "image", "detection_threshold": 0.5, "required_tools": ["groundingdino", "MLLM"], "evidence_source": "visual_grounding_and_multimodal_analysis"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'flag', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.5, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.5 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 flag 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 flag 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.5 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'flag', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.5, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.5 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 flag 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 flag 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 flag 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
