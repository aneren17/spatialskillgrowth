"""Executable SpatialSkillGrowth Skill: pedestrian_queue_detector."""

WORKFLOW_ID = 'pedestrian_queue_3f406b278470'
PROBLEM_CLASS = 'pedestrian_queue'
WORKFLOW_GRAPH_SHA256 = 'b7df6a5c01d46a644f22cc23666aee105389c5aaefaf1a52c5463ab81aa7700b'
DECLARED_TOOLS = ('paddleHeadDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'pedestrian_queue_3f406b278470', 'name': 'pedestrian_queue_detector', 'problem_class': 'pedestrian_queue', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'MLLM'], 'description': '基于静态图像输入，利用人头检测工具提取视觉证据，并结合多模态大语言模型判断场景中是否存在行人排队聚集异常事件。该工作流严格依赖 `paddleHeadDetTool` 提供的检测框作为空间分布证据，由 `MLLM` 综合评估人群排列形态以确认 `pedestrian_queue` 事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非 `pedestrian_queue` 类别的其他异常事件检测任务; 无法通过人头检测工具获取有效空间分布证据的极端遮挡或低分辨率场景', 'capability_boundary': '{"supported_event_type": "pedestrian_queue", "supported_media_type": "image", "required_tools": ["paddleHeadDetTool", "MLLM"], "evidence_requirement": "必须包含由 paddleHeadDetTool 生成的人头检测框坐标及数量信息，作为 MLLM 判断排队形态的必要输入", "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 pedestrian_queue 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 pedestrian_queue 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0']}]}


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

    # 依据图像证据判断 pedestrian_queue 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 pedestrian_queue 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 pedestrian_queue 异常事件。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
