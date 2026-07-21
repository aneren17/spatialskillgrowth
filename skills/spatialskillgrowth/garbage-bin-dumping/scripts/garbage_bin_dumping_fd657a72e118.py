"""Executable SpatialSkillGrowth Skill: garbage_bin_dumping_detector."""

WORKFLOW_ID = 'garbage_bin_dumping_fd657a72e118'
PROBLEM_CLASS = 'garbage_bin_dumping'
WORKFLOW_GRAPH_SHA256 = '97c5733efa0f09ab235e6a31c695bfa9b89d25dc0a6cd88dc893a1ecb79e3367'
DECLARED_TOOLS = ('groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'garbage_bin_dumping_fd657a72e118', 'name': 'garbage_bin_dumping_detector', 'problem_class': 'garbage_bin_dumping', 'required_slots': [], 'required_tools': ['groundingdino', 'unidepth', 'MLLM'], 'description': '检测输入图像中是否发生垃圾桶倾倒异常事件。通过 GroundingDINO 定位垃圾桶及潜在倾倒物，结合 UniDepth 分析空间深度关系，最终由多模态大模型依据视觉证据判定是否存在倾倒行为。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 garbage_bin_dumping 类别的其他异常事件; 无法通过开放词汇检测定位垃圾桶或相关物体的场景', 'capability_boundary': '仅针对图像输入执行垃圾桶倾倒检测，依赖 GroundingDINO 的开放词汇检测能力与 UniDepth 的深度估计，最终由 MLLM 进行语义判断。不处理视频流、音频或非视觉模态数据。', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'garbage_bin_dumping', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 garbage_bin_dumping 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'garbage_bin_dumping', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 garbage_bin_dumping 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 garbage_bin_dumping 异常事件。',
        depends_on=['groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
