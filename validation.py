"""validate_question and screen_question from the Interface Contracts."""

import json
import re
from typing import Literal

from .models import input_error

MAX_BODY_BYTES = 16 * 1024
MAX_QUESTION_CODE_POINTS = 1000


def check_media_type(content_type: str | None) -> None:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise input_error(415, "Please send the question as application/json.")


def parse_json(body: bytes) -> object:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise input_error(400, "The request was not valid JSON. Please try again.")


def validate_question(payload: object) -> str:
    """Check the object, field type, and length. Return the trimmed text."""
    if not isinstance(payload, dict) or set(payload) != {"question"}:
        raise input_error(422, "Send one field named question.")
    question = payload["question"]
    if not isinstance(question, str):
        raise input_error(422, "The question must be text.")
    question = question.strip()
    if not question:
        raise input_error(422, "Please enter a question.")
    if len(question) > MAX_QUESTION_CODE_POINTS:  # len() counts Unicode code points
        raise input_error(422, "Please use 1,000 characters or fewer.")
    return question


# Screening patterns: email addresses, common US phone numbers, SSN-like numbers.
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_SSN = re.compile(r"(?<!\d)\d{3}[\s-]?\d{2}[\s-]?\d{4}(?!\d)")

PrivacyDecision = Literal["allow", "reject"]


def screen_question(question: str) -> PrivacyDecision:
    for pattern in (_EMAIL, _PHONE, _SSN):
        if pattern.search(question):
            return "reject"
    return "allow"


def require_allowed(question: str) -> None:
    if screen_question(question) == "reject":
        # Identify the correction without echoing the input.
        raise input_error(
            422,
            "Your question looks like it contains personal information, such as an email address, "
            "phone number, or Social Security number. Please remove it and try again.",
        )
