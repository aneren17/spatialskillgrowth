"""Executable SpatialSkillGrowth Skill: instrument_operation_detector."""

WORKFLOW_ID = 'instrument_operation_f06dd7f53eb7'
PROBLEM_CLASS = 'instrument_operation'
WORKFLOW_GRAPH_SHA256 = 'd194440190d738a75f28fc712837f782ad65fa3dc2bb8fa56eec2b9e0d201e48'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'instrument_operation_f06dd7f53eb7', 'name': 'instrument_operation_detector', 'problem_class': 'instrument_operation', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大语言模型（MLLM）分析输入图像，检测是否存在针对仪器的操作行为。该工作流通过视觉证据判断是否发生仪器操作异常事件，输出二元判断结果。', 'exclusions': '非图像类型的媒体输入; 涉及非仪器对象的操作场景; 需要调用 embeddingTool 的文本或向量嵌入任务', 'capability_boundary': '{"supported_event_type": "instrument_operation", "supported_media_type": "image", "required_evidence": "图像中可见的仪器操作行为视觉特征", "output_format": "布尔值（是/否）", "tool_dependency": "MLLM"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 instrument_operation 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 instrument_operation 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 instrument_operation 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 instrument_operation 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 instrument_operation 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
