"""FastAPI server: serves Alex's page and the POST /api/questions endpoint."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from . import ai_adapter, search
from .config import PROJECT_ROOT, Settings, load_settings
from .models import HR_GUIDANCE_MESSAGE, ContractError, ContractResult, input_error, service_error
from .responses import build_response
from .validation import MAX_BODY_BYTES, check_media_type, parse_json, require_allowed, validate_question

# Log only outcomes and timings. Raw questions, prompts, and model output are never logged.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("onboarding")

STATIC_DIR = PROJECT_ROOT / "static"
SEARCH_LIMIT = 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    if not settings.database_path.exists():
        count = search.build_index(settings.documents_dir, settings.database_path)
        log.info("Built search index with %d passages", count)
    log.info("AI provider: %s", settings.ai_provider)
    app.state.settings = settings
    yield


app = FastAPI(title="Maple Ridge Onboarding Assistant", lifespan=lifespan, docs_url=None, redoc_url=None)


def to_response(result: ContractResult, extra_headers: dict | None = None) -> JSONResponse:
    headers = {"Cache-Control": "no-store", **(extra_headers or {})}
    return JSONResponse(result.body(), status_code=result.status_code, headers=headers)


async def read_capped_body(request: Request) -> bytes:
    """Read the body, stopping once it passes 16 KiB (checked before parsing)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise input_error(413, "Your question is too long. Please shorten it.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise input_error(413, "Your question is too long. Please shorten it.")
    return bytes(body)


async def handle_question(request: Request, settings: Settings) -> ContractResult:
    body = await read_capped_body(request)
    # The 15 seconds start once the complete body has arrived.
    deadline = time.monotonic() + settings.deadline_seconds

    check_media_type(request.headers.get("content-type"))
    question = validate_question(parse_json(body))
    require_allowed(question)

    passages = await search.search_passages(question, SEARCH_LIMIT, deadline, settings.database_path)
    if not passages:
        return ContractResult(200, "hr_guidance", HR_GUIDANCE_MESSAGE)  # no AI call

    answer = await ai_adapter.generate_answer(question, passages, deadline, settings)
    if time.monotonic() > deadline:
        raise service_error(504, "The assistant took too long to answer. Please try again.")
    return build_response(answer, passages)


@app.post("/api/questions")
async def questions(request: Request) -> JSONResponse:
    started = time.monotonic()
    try:
        result = await handle_question(request, request.app.state.settings)
    except ContractError as exc:
        result = exc.result()
    except Exception:
        log.exception("Unexpected failure while handling a question")
        result = service_error(500).result()
    log.info(
        "question result=%s status=%d sources=%d ms=%d",
        result.result_type, result.status_code, len(result.sources), (time.monotonic() - started) * 1000,
    )
    return to_response(result)


@app.api_route("/api/questions", methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def questions_wrong_method() -> JSONResponse:
    result = input_error(405, "Use POST to send a question.").result()
    return to_response(result, {"Allow": "POST"})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})
