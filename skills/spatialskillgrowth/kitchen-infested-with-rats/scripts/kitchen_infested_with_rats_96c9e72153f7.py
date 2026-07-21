"""Executable SpatialSkillGrowth Skill: kitchen_infested_with_rats_image_baseline."""

WORKFLOW_ID = 'kitchen_infested_with_rats_96c9e72153f7'
PROBLEM_CLASS = 'kitchen_infested_with_rats'
WORKFLOW_GRAPH_SHA256 = 'b3ce39d48fcc4122065eeea9d82890fd2ad5afd94385f775334bda84210da1db'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'kitchen_infested_with_rats_96c9e72153f7', 'name': 'kitchen_infested_with_rats_image_baseline', 'problem_class': 'kitchen_infested_with_rats', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '使用单张图片或视频代表帧判断 kitchen_infested_with_rats 异常事件。', 'exclusions': '不处理原始视频时序，只依据当前图片证据。', 'capability_boundary': '必须取得 MLLM 基于可见画面的明确判断。', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 kitchen_infested_with_rats 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 kitchen_infested_with_rats 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 kitchen_infested_with_rats 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
