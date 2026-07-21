"""Executable SpatialSkillGrowth Skill: fire_detection_image."""

WORKFLOW_ID = 'fire_ea9123696534'
PROBLEM_CLASS = 'fire'
WORKFLOW_GRAPH_SHA256 = '274cf184e411bf67d09dd0fa3b9bc667d5925a456d1edcf021de8a3d69f35a0a'
DECLARED_TOOLS = ('python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fire_ea9123696534', 'name': 'fire_detection_image', 'problem_class': 'fire', 'required_slots': [], 'required_tools': ['python_code_sandbox', 'MLLM'], 'description': '基于多模态大模型（MLLM）和结构化证据分析，检测输入图像中是否存在“起火”异常事件。工作流首先通过代码沙箱计算视觉证据摘要，随后由 MLLM 依据图像特征进行最终判断。', 'exclusions': '禁止使用 embeddingTool 处理图像输入。; 仅适用于静态图像输入，不支持视频流或音频数据。; 仅检测“起火”这一特定异常类别，不泛化至烟雾、爆炸或其他火灾相关现象，除非证据明确指向明火。; 不适用于需要实时低延迟响应的场景，因涉及代码执行与多模态推理。', 'capability_boundary': '{"input_media": "image", "event_type": "fire", "evidence_requirement": "必须包含通过 python_code_sandbox 生成的结构化视觉证据摘要，以及 MLLM 基于图像像素特征对明火存在的直接判定。", "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'python_code_sandbox', 'args': {'code': ''}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fire 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 fire 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': ''},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=[],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 fire 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fire 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire 异常事件。',
        depends_on=['python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
