"""Executable SpatialSkillGrowth Skill: climbing_disconnection_detector."""

WORKFLOW_ID = 'climbing_disconnection_d8a9b55f4b0d'
PROBLEM_CLASS = 'climbing_disconnection'
WORKFLOW_GRAPH_SHA256 = 'b1a2fd8dd9762fa0e53487a4af15e9b837b2e3c9c7ffb3c6146a6fe0abcb7ee8'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'climbing_disconnection_d8a9b55f4b0d', 'name': 'climbing_disconnection_detector', 'problem_class': 'climbing_disconnection', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大语言模型（MLLM）分析输入图像，检测是否存在‘攀爬脱网’异常事件。该工作流通过视觉证据判断目标主体是否出现攀爬过程中脱离防护网或安全约束的状态，适用于静态图像场景下的特定安全违规检测。', 'exclusions': '不适用于视频流或动态序列分析，仅处理单张静态图像。; 不适用于非攀爬类异常（如跌倒、入侵、火灾等），仅针对攀爬行为中的脱网状态。; 不适用于无清晰视觉证据或图像质量严重受损导致无法识别主体与防护网关系的场景。; 不执行目标物体名称的泛化抽象，因工具图未提供可替换目标的运行时槽位，检测器严格限定于‘攀爬脱网’这一具体事件类型。', 'capability_boundary': '{"required_evidence": ["图像中必须包含可识别的攀爬主体（如人员）与防护网结构。", "必须存在主体与防护网空间关系异常的视觉特征（如主体悬空、脱离网面接触点）。", "MLLM 需基于上述视觉证据输出明确的是/否判断，不得依赖外部文本或嵌入向量工具。"], "tool_constraints": ["禁止调用 embeddingTool，所有视觉分析必须通过图像工具与多模态模型完成。", "工具图固定为单步 MLLM 推理，无前置预处理或后处理步骤。"], "output_format": "仅返回‘是’或‘否’作为最终判断结果。"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 climbing_disconnection 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 climbing_disconnection 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 climbing_disconnection 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 climbing_disconnection 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 climbing_disconnection 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
