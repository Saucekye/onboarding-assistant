"""build_response: checks the model's decision and citations against retrieved passages."""

from .models import HR_GUIDANCE_MESSAGE, ContractResult, ModelAnswer, SourcePassage, service_error

MAX_MESSAGE_CODE_POINTS = 4000
MAX_SOURCES = 3


def build_response(result: ModelAnswer, retrieved: list[SourcePassage]) -> ContractResult:
    if result.decision == "hr_guidance":
        # A decline always gets the standard HR message, whatever the model wrote.
        return ContractResult(200, "hr_guidance", HR_GUIDANCE_MESSAGE)

    if result.decision != "answer":
        raise service_error(502)

    message = result.message.strip()
    if not message or len(message) > MAX_MESSAGE_CODE_POINTS:
        raise service_error(502)

    # Remove duplicate IDs, keeping first-cited order.
    cited = list(dict.fromkeys(result.passage_ids))
    by_id = {p.passage_id: p for p in retrieved}
    if not cited or len(cited) > MAX_SOURCES or any(pid not in by_id for pid in cited):
        raise service_error(502)  # missing or unknown citation

    # Sources come from the stored rows, never from model text.
    return ContractResult(200, "answer", message, [by_id[pid] for pid in cited])
