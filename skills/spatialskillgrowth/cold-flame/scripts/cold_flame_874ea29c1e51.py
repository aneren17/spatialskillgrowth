"""Executable SpatialSkillGrowth Skill: cold_flame_detector."""

WORKFLOW_ID = 'cold_flame_874ea29c1e51'
PROBLEM_CLASS = 'cold_flame'
WORKFLOW_GRAPH_SHA256 = '4a4628632f1989bb270073af2aa98be028039a33b04fd2ca3776e092010db169'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'cold_flame_874ea29c1e51', 'name': 'cold_flame_detector', 'problem_class': 'cold_flame', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于图像输入，利用多模态大模型（MLLM）分析视觉特征，检测是否存在冷焰火（cold_flame）异常事件。该工作流专注于从静态图像中提取与冷焰火相关的视觉证据，并据此输出二分类判断结果。', 'exclusions': '禁止使用 embeddingTool 处理图像输入。; 不适用于视频流、音频或纯文本描述的异常检测。; 不适用于其他类型的火焰异常（如明火、爆炸火焰）或与非冷焰火相关的视觉异常。; 不包含对异常事件的原因分析、修复建议或历史趋势评估。', 'capability_boundary': '{"input_modality": "image", "event_type": "cold_flame", "evidence_source": "visual_features_via_mllm", "output_format": "binary_classification", "tool_constraints": "仅允许使用 MLLM 工具进行图像分析和判断，不得引入外部知识库或额外推理步骤。"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 cold_flame 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 cold_flame 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 cold_flame 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 cold_flame 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 cold_flame 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
