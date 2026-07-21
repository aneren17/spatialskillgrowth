"""Executable SpatialSkillGrowth Skill: forest_fire_detector."""

WORKFLOW_ID = 'forest_fire_2c91fe8e39d2'
PROBLEM_CLASS = 'forest_fire'
WORKFLOW_GRAPH_SHA256 = '7c0045d12d721ecee3de4d9e1a722be2a4c897da8f7ac3ef7538d9f6c490e923'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'forest_fire_2c91fe8e39d2', 'name': 'forest_fire_detector', 'problem_class': 'forest_fire', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于单张输入图像，利用多模态大语言模型（MLLM）分析视觉特征，检测是否存在森林火灾异常事件。该工作流专注于通过图像证据识别火灾相关的视觉信号（如烟雾、明火、焦痕等），并输出二元判断结果。', 'exclusions': '不支持视频流、音频或非图像类型的媒体输入。; 不执行火灾原因分析、火势蔓延预测或损失评估。; 不处理非森林环境（如城市建筑火灾、工业火灾）的检测，除非视觉特征与森林火灾高度相似且无其他上下文排除。; 禁止使用 embeddingTool 进行图像嵌入处理。', 'capability_boundary': '{"event_type": "forest_fire", "media_type": "image", "required_evidence": "视觉证据（如烟雾、火焰、燃烧痕迹）", "output_format": "binary (是/否)"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 forest_fire 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 forest_fire 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 forest_fire 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 forest_fire 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 forest_fire 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
