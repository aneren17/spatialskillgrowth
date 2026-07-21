"""Executable SpatialSkillGrowth Skill: without_wearing_clothes_detector."""

WORKFLOW_ID = 'without_wearing_clothes_d3df6fb17d3e'
PROBLEM_CLASS = 'without_wearing_clothes'
WORKFLOW_GRAPH_SHA256 = '6d0460ab0487c39d611e1af75f4b82151f6d2574bf1f3ca41f82e7c10e5ac7e3'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'without_wearing_clothes_d3df6fb17d3e', 'name': 'without_wearing_clothes_detector', 'problem_class': 'without_wearing_clothes', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '检测输入图像中是否存在人员未穿防护服的异常事件。工作流首先通过 paddleHeadDetTool 定位可见人头，随后利用多模态大语言模型（MLLM）结合视觉证据判断该区域是否满足未穿防护服的特征条件。', 'exclusions': '非图像类型的媒体输入; 图像中未检测到可见人头的场景; 需要调用 embeddingTool 的场景; 非 without_wearing_clothes 类别的异常检测任务', 'capability_boundary': '{"input_media": "image", "event_type": "without_wearing_clothes", "required_evidence": ["paddleHeadDetTool 检测到的人头边界框", "MLLM 基于人头区域视觉特征对防护服穿戴状态的判定"], "constraints": ["禁止使用 embeddingTool", "必须依赖工具图定义的步骤顺序执行", "仅针对已确定的 without_wearing_clothes 类别进行二元判断"]}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 without_wearing_clothes 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 without_wearing_clothes 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

    # 依据图像证据判断 without_wearing_clothes 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 without_wearing_clothes 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 without_wearing_clothes 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
