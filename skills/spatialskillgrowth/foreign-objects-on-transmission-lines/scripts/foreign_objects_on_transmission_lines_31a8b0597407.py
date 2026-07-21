"""Executable SpatialSkillGrowth Skill: foreign_objects_on_transmission_lines."""

WORKFLOW_ID = 'foreign_objects_on_transmission_lines_31a8b0597407'
PROBLEM_CLASS = 'foreign_objects_on_transmission_lines'
WORKFLOW_GRAPH_SHA256 = '686da5b5e7a486b52fc8829bed9c35c74e805351f07e1ff3a121ebd3f42044c0'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'foreign_objects_on_transmission_lines_31a8b0597407', 'name': 'foreign_objects_on_transmission_lines', 'problem_class': 'foreign_objects_on_transmission_lines', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于图像输入，利用开放词汇目标检测（GroundingDINO）定位潜在异物，并结合多模态大模型（MLLM）分析视觉证据，判断输电线路是否存在异物附着异常。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非输电线路场景（如配电线路、通信光缆等，除非工具图槽位明确支持泛化）; 未包含 groundingdino 和 MLLM 工具依赖的运行环境', 'capability_boundary': '{"event_type": "foreign_objects_on_transmission_lines", "media_type": "image", "detection_threshold": 0.3, "evidence_requirement": "必须通过 groundingdino 检测到的目标框及 MLLM 对图像内容的语义分析作为判断依据", "output_format": "二元分类（是/否）"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': "使用 'foreign object', 'plastic bag', 'balloon', 'debris' 等关键词检测输电线路上的异物", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 foreign_objects_on_transmission_lines 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用 'foreign object', 'plastic bag', 'balloon', 'debris' 等关键词检测输电线路上的异物", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 foreign_objects_on_transmission_lines 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
