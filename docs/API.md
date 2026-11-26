# API reference

The server exposes one JSON endpoint for questions and two routes that serve the web page. The behavior below comes from our submitted Interface Contracts and is checked by `tests/test_api.py`.

## `POST /api/questions`

Ask one question. The server searches the HR documents, asks the AI provider to answer from the top three passages, and checks the answer before returning it.

### Request

- Header: `Content-Type: application/json`
- Body: exactly one field, `question`.

```json
{ "question": "What time should I arrive on my first day?" }
```

Rules (checked before any search or AI call):

| Rule | Limit |
| --- | --- |
| Request body size | 16 KiB |
| Question length | 1 to 1,000 characters (counted as Unicode code points, after trimming) |
| Fields | `question` only, as text |
| Privacy screening | Rejects text that looks like an email address, US phone number, or Social Security number |

### Response

Every response, success or error, has the same three fields and the header `Cache-Control: no-store`.

```json
{
  "result_type": "answer",
  "message": "Arrive at 8:30 a.m. on your first day and check in at the front desk in the lobby of Building A.",
  "sources": [
    {
      "document_id": "HR-01",
      "passage_id": "HR-01-P2",
      "document_title": "HR-01 New-Hire Orientation",
      "passage_text": "New employees start on a Monday. Arrive at 8:30 a.m. and check in at the front desk in the lobby of Building A. ..."
    }
  ]
}
```

`sources` is empty unless `result_type` is `answer`. Source fields are read from our own database, never from the AI's text, and every cited passage must be one of the (up to three) passages that search returned.

### Result types and status codes

| `result_type` | HTTP | When |
| --- | --- | --- |
| `answer` | 200 | The documents answer the question. `sources` lists the 1 to 3 passages used. |
| `hr_guidance` | 200 | Search found nothing, or the AI declined. The message is always "The available documents do not answer this question. Please contact HR." |
| `input_error` | 400 | Body is not valid JSON |
| `input_error` | 405 | Method other than POST (response includes `Allow: POST`) |
| `input_error` | 413 | Body larger than 16 KiB |
| `input_error` | 415 | `Content-Type` is not `application/json` |
| `input_error` | 422 | Wrong fields, empty question, over 1,000 characters, or personal information detected |
| `service_error` | 500 | Unexpected server failure |
| `service_error` | 502 | The AI's reply was malformed, uncited, or cited a passage that was not retrieved |
| `service_error` | 503 | The AI provider is not configured (missing or unknown provider, model, or key), rejected the request (for example a bad key, HTTP 401), or could not be reached |
| `service_error` | 504 | The 15-second deadline passed |

### Timing

One 15-second deadline covers search and the AI call together. It starts once the full request body has arrived. In our real-provider run, responses took 1.2 to 2.9 seconds (see `alpha-results.md`).

### Privacy

The server logs only the result type, status code, number of sources, and elapsed milliseconds. Questions, prompts, and AI replies are never logged. The API key is read only on the server and is never sent to the browser.

### Example with curl

```bash
curl -s -X POST http://127.0.0.1:8000/api/questions \
  -H "Content-Type: application/json" \
  -d '{"question": "Where can employees park?"}'
```

## Page routes

| Route | Returns |
| --- | --- |
| `GET /` | The question page (`static/index.html`) |
| `GET /app.js` | The page's script (`static/app.js`) |

The built-in FastAPI documentation pages (`/docs`, `/redoc`) are turned off, so this file is the API documentation.
