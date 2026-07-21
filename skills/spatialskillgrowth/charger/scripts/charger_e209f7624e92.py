"""Executable SpatialSkillGrowth Skill: charger_anomaly_detection."""

WORKFLOW_ID = 'charger_e209f7624e92'
PROBLEM_CLASS = 'charger'
WORKFLOW_GRAPH_SHA256 = 'b308b472fad4d4a8e750adf315015168fcedc205b0cdea5583a8cf19126072ed'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'charger_e209f7624e92', 'name': 'charger_anomaly_detection', 'problem_class': 'charger', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大语言模型（MLLM）分析输入图像，检测充电器是否处于未归位状态。该工作流通过视觉证据直接判断异常事件，适用于静态图像输入场景。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征提取的场景; 充电器归位状态正常（即已正确归位）的常规场景; 涉及充电器物理损坏、线路断裂等其他类型硬件故障的检测; 需要动态时序分析或连续监控的场景', 'capability_boundary': '{"input_modality": "image", "event_type": "charger", "anomaly_definition": "充电器未归位", "reasoning_method": "visual_evidence_based_mllm", "output_format": "binary_classification"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 charger 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 charger 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 charger 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 charger 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 charger 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
