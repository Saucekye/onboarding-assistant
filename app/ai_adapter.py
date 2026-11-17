"""generate_answer: the only code that talks to the hosted language model.

The provider is chosen in .env with AI_PROVIDER:
  fake       No network call. Cites the top search match, labeled as test mode,
             so everyone can run the starter before SP-1 picks a provider.
  anthropic  Anthropic Messages API.
  openai     OpenAI Chat Completions API.

Whatever the provider returns is translated into a ModelAnswer here, so the rest
of the server (and the browser) never depends on a provider's format.
"""

import asyncio
import json
import logging
import time

import httpx

from .config import Settings
from .models import ModelAnswer, SourcePassage, service_error

log = logging.getLogger("onboarding.ai")

SYSTEM_PROMPT = """You answer new employees' questions using ONLY the policy passages provided.

Rules:
- Use only facts stated in the passages. Never add policy details, numbers, or advice that the passages do not state.
- If the passages do not contain the requested fact, decline: set "decision" to "hr_guidance" and "passage_ids" to [].
- If you answer, cite every passage you relied on by its exact passage ID.
- Keep the answer short and plain. Do not include the passage IDs in the message text.

Reply with a single JSON object and nothing else:
{"decision": "answer" or "hr_guidance", "message": "<answer text>", "passage_ids": ["<ID>", ...]}"""


def build_user_prompt(question: str, passages: list[SourcePassage]) -> str:
    blocks = [f"[{p.passage_id}] ({p.document_title})\n{p.passage_text}" for p in passages]
    return "Passages:\n\n" + "\n\n".join(blocks) + f"\n\nEmployee question:\n{question}"


def parse_model_json(text: str) -> ModelAnswer:
    """Turn the model's text into a ModelAnswer. Malformed output is a 502."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
    try:
        data = json.loads(cleaned)
    except ValueError:
        raise service_error(502)
    if not isinstance(data, dict):
        raise service_error(502)
    decision, message, ids = data.get("decision"), data.get("message", ""), data.get("passage_ids", [])
    if not isinstance(decision, str) or not isinstance(message, str) or not isinstance(ids, list):
        raise service_error(502)
    if not all(isinstance(i, str) for i in ids):
        raise service_error(502)
    return ModelAnswer(decision=decision, message=message, passage_ids=ids)


async def _call_anthropic(client: httpx.AsyncClient, s: Settings, user_prompt: str) -> str:
    r = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": s.ai_api_key, "anthropic-version": "2023-06-01"},
        json={
            "model": s.ai_model,
            "max_tokens": 600,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
    )
    r.raise_for_status()
    return "".join(part.get("text", "") for part in r.json().get("content", []))


async def _call_openai(client: httpx.AsyncClient, s: Settings, user_prompt: str) -> str:
    r = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {s.ai_api_key}"},
        json={
            "model": s.ai_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


PROVIDERS = {"anthropic": _call_anthropic, "openai": _call_openai}


def _fake_answer(passages: list[SourcePassage]) -> ModelAnswer:
    top = passages[0]
    return ModelAnswer(
        decision="answer",
        message=(
            "[Test mode: no AI provider is configured.] The closest matching passage is "
            f"{top.passage_id}. Open the source below to read it."
        ),
        passage_ids=[top.passage_id],
    )


async def generate_answer(question: str, passages: list[SourcePassage], deadline: float, settings: Settings) -> ModelAnswer:
    if settings.ai_provider == "fake":
        return _fake_answer(passages)

    call = PROVIDERS.get(settings.ai_provider)
    if call is None or not settings.ai_api_key or not settings.ai_model:
        log.error("AI provider is not configured correctly (check AI_PROVIDER, AI_MODEL, AI_API_KEY in .env)")
        raise service_error(503)

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise service_error(500)

    try:
        async with httpx.AsyncClient(timeout=remaining) as client:
            text = await asyncio.wait_for(call(client, settings, build_user_prompt(question, passages)), remaining)
    except (TimeoutError, httpx.TimeoutException):
        raise service_error(504, "The assistant took too long to answer. Please try again.")
    except httpx.HTTPStatusError as exc:
        # Status code only: never log the request, prompt, or response body.
        log.warning("AI provider returned HTTP %s", exc.response.status_code)
        raise service_error(503)
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        log.warning("AI provider request failed")
        raise service_error(503)

    return parse_model_json(text)
