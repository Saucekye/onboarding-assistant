"""Data shapes shared across components, matching the Interface Contracts."""

from dataclasses import dataclass, field
from typing import Literal

ResultType = Literal["answer", "hr_guidance", "input_error", "service_error"]

HR_GUIDANCE_MESSAGE = "The available documents do not answer this question. Please contact HR."


@dataclass(frozen=True)
class SourcePassage:
    document_id: str
    passage_id: str
    document_title: str
    passage_text: str


@dataclass(frozen=True)
class ModelAnswer:
    decision: str              # "answer" or "hr_guidance"
    message: str
    passage_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContractResult:
    status_code: int
    result_type: ResultType
    message: str
    sources: list[SourcePassage] = field(default_factory=list)

    def body(self) -> dict:
        return {
            "result_type": self.result_type,
            "message": self.message,
            "sources": [vars(s) for s in self.sources],
        }


class ContractError(Exception):
    """Stops processing and becomes an error response with the same three fields."""

    def __init__(self, status_code: int, result_type: ResultType, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.result_type = result_type
        self.message = message

    def result(self) -> ContractResult:
        return ContractResult(self.status_code, self.result_type, self.message)


def input_error(status_code: int, message: str) -> ContractError:
    return ContractError(status_code, "input_error", message)


def service_error(status_code: int, message: str = "We couldn’t get an answer. Please try again.") -> ContractError:
    return ContractError(status_code, "service_error", message)
