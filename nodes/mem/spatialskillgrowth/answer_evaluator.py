"""Ground-truth evaluator used only by the exploration entrypoint."""

import re


FLOAT_ZERO_ABSOLUTE_TOLERANCE = 0.1
FLOAT_RELATIVE_TOLERANCE = 0.1


def answer_matches(prediction: str, groundtruth: str) -> bool:
    pred = normalize_answer(prediction)
    aliases = [
        normalize_answer(item)
        for item in re.split(r"<OR>|\||\n", str(groundtruth or ""), flags=re.I)
        if item.strip()
    ]
    if not pred or not aliases:
        return False
    pred_compact = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", pred)
    for truth in aliases:
        truth_compact = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", truth)
        if not truth_compact:
            continue
        if pred_compact == truth_compact:
            return True
    return False


def normalize_answer(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^(?:final\s+answer|answer)\s*[:：]\s*", "", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff.\-]+", " ", text)
    return " ".join(text.split()).rstrip(".")


def answer_matches_typed(
    prediction: str,
    groundtruth: str,
    answer_type: str,
) -> bool:
    normalized_type = str(answer_type or "").strip().lower()
    if normalized_type not in {"float", "int"}:
        return answer_matches(prediction, groundtruth)
    pred_number = _extract_number(prediction)
    truth_number = _extract_number(groundtruth)
    if pred_number is None or truth_number is None:
        return False
    if normalized_type == "int":
        prediction_text = str(prediction or "").strip().replace(",", "")
        return bool(re.fullmatch(r"[-+]?\d+", prediction_text)) and (
            int(prediction_text) == int(round(truth_number))
        )
    difference = abs(pred_number - truth_number)
    if truth_number == 0:
        return difference < FLOAT_ZERO_ABSOLUTE_TOLERANCE
    return difference / abs(truth_number) < FLOAT_RELATIVE_TOLERANCE


def _extract_number(value: str):
    match = re.fullmatch(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
        str(value or "").strip().replace(",", ""),
    )
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None
