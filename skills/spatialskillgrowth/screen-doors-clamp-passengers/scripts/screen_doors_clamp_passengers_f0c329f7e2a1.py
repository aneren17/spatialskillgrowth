"""Executable SpatialSkillGrowth Skill: screen_doors_clamp_passengers_detector."""

WORKFLOW_ID = 'screen_doors_clamp_passengers_f0c329f7e2a1'
PROBLEM_CLASS = 'screen_doors_clamp_passengers'
WORKFLOW_GRAPH_SHA256 = 'dae4346a02d2faa65b1a0a5a6c0a733819755bcb6907eaa6644627678fcfff86'
DECLARED_TOOLS = ('groundingdino', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'screen_doors_clamp_passengers_f0c329f7e2a1', 'name': 'screen_doors_clamp_passengers_detector', 'problem_class': 'screen_doors_clamp_passengers', 'required_slots': [], 'required_tools': ['groundingdino', 'MLLM'], 'description': '基于视觉证据检测屏蔽门夹人异常事件。工作流首先利用开放词汇检测工具（GroundingDINO）在图像中定位与屏蔽门及乘客相关的视觉目标，随后通过多模态大语言模型（MLLM）结合检测证据进行综合研判，以确认是否发生屏蔽门夹人事件。', 'exclusions': '非图像类型的媒体输入; 非屏蔽门夹人（screen_doors_clamp_passengers）类别的异常检测任务; 需要调用 embeddingTool 的场景', 'capability_boundary': '仅适用于图像模态下的屏蔽门夹人事件检测。检测能力依赖于 GroundingDINO 的开放词汇定位精度及 MLLM 的视觉推理能力，不包含对视频流、音频或其他类型异常事件的检测支持。', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': '使用低阈值检测关键对象边缘及附近主体，捕捉微小遮挡或接触区域', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 screen_doors_clamp_passengers 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': '使用低阈值检测关键对象边缘及附近主体，捕捉微小遮挡或接触区域', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 依据图像证据判断 screen_doors_clamp_passengers 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 screen_doors_clamp_passengers 异常事件。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
