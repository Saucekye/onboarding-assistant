"""Check the AI provider settings in .env with one tiny request. Never prints any part of the secret.

Usage:  python -m scripts.check_provider

Reports whether the key looks well-formed (length, stray spaces or quotes) and what the
provider answers. Use it when the app shows service errors (HTTP 401 = the provider
rejected the key; 404 = the model name is wrong).
"""

import httpx

from app.config import load_settings


def describe_response(response: httpx.Response) -> str:
    try:
        error = response.json().get("error", {})
        return f"HTTP {response.status_code}  type={error.get('type')}  message={error.get('message')}"
    except ValueError:
        return f"HTTP {response.status_code}"


def main() -> None:
    s = load_settings()
    print(f"AI_PROVIDER = {s.ai_provider!r}")
    print(f"AI_MODEL    = {s.ai_model!r}")
    key = s.ai_api_key
    if not key:
        print("AI_API_KEY is empty. Check that .env is saved in the project folder with the three lines.")
        return
    # Show only the fixed 7-character prefix (never any of the secret part).
    starts_ok = key.startswith("sk-ant-")
    print(f"AI_API_KEY  : {len(key)} characters, {'starts with sk-ant-' if starts_ok else 'does NOT start with sk-ant-'}")
    problems = [name for name, bad in (("a space", " " in key), ("a quote mark", '"' in key or "'" in key)) if bad]
    if problems:
        print("WARNING: the key contains " + " and ".join(problems) + ". Remove it from .env.")
    if s.ai_provider != "anthropic":
        print("This check only covers AI_PROVIDER=anthropic.")
        return

    body = {"model": s.ai_model, "max_tokens": 16, "messages": [{"role": "user", "content": "Reply with the word OK."}]}
    url = "https://api.anthropic.com/v1/messages"
    attempts = {
        "x-api-key header (what the app uses)": {"x-api-key": key, "anthropic-version": "2023-06-01"},
        "Authorization: Bearer header": {"Authorization": f"Bearer {key}", "anthropic-version": "2023-06-01"},
    }
    for label, headers in attempts.items():
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=20)
        except httpx.HTTPError as exc:
            print(f"{label}: could not connect ({type(exc).__name__})")
            continue
        verdict = "WORKS" if response.status_code == 200 else "failed"
        print(f"{label}: {verdict}  {describe_response(response)}")


if __name__ == "__main__":
    main()
