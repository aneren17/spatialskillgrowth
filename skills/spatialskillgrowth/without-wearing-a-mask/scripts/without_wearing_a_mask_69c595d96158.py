"""Executable SpatialSkillGrowth Skill: without_wearing_a_mask."""

WORKFLOW_ID = 'without_wearing_a_mask_69c595d96158'
PROBLEM_CLASS = 'without_wearing_a_mask'
WORKFLOW_GRAPH_SHA256 = '1524119930686110d8df60609eba0ffdf00e9e3bafcdaa972f916e15a4dd37e4'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'without_wearing_a_mask_69c595d96158', 'name': 'without_wearing_a_mask', 'problem_class': 'without_wearing_a_mask', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '基于图像输入，通过检测可见人头并结合多模态视觉证据，判断场景中是否存在人员未佩戴口罩的异常事件。', 'exclusions': '非图像类型的媒体输入; 图像中未检测到可见人头的场景; 涉及面部遮挡物（如围巾、口罩）但非标准医用或防护口罩的模糊边界情况，需依赖多模态模型对视觉证据的明确判定', 'capability_boundary': '{"event_type": "without_wearing_a_mask", "media_type": "image", "required_evidence": ["通过 paddleHeadDetTool 检测到的可见人头区域", "多模态大语言模型（MLLM）基于人头区域视觉特征对是否佩戴口罩的判定结果"], "constraints": ["禁止使用 embeddingTool 处理图像输入", "最终输出必须为二值判断（是/否）", "检测范围仅限于工具图定义的可见人头区域，不泛化至全身或其他身体部位"]}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 without_wearing_a_mask 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 without_wearing_a_mask 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


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

    # 依据图像证据判断 without_wearing_a_mask 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 without_wearing_a_mask 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 without_wearing_a_mask 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
