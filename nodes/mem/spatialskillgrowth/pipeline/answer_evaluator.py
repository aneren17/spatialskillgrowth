"""探索阶段的异常判断答案比对。"""


TRUE_ANSWERS = {"yes", "true", "1", "是", "有", "发生", "异常"}
FALSE_ANSWERS = {"no", "false", "0", "否", "无", "未发生", "正常"}


def normalize_bool(value):
    normalized = str(value or "").strip().lower()
    if normalized in TRUE_ANSWERS:
        return True
    if normalized in FALSE_ANSWERS:
        return False
    return None


def answer_matches(prediction, groundtruth):
    prediction_value = normalize_bool(prediction)
    groundtruth_value = normalize_bool(groundtruth)
    if prediction_value is None or groundtruth_value is None:
        return False
    return prediction_value == groundtruth_value
