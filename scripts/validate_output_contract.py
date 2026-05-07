from __future__ import annotations

import argparse
import json
import sys
from urllib import parse as urllib_parse
from urllib import request as urllib_request


STANDARD_QUESTIONS = [
    "What does this project do?",
    "Why does this project exist?",
    "I'm new to this project. Where do I start?",
]


def _http_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_text(url: str) -> str:
    with urllib_request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def _load_terms(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.strip().startswith("#")]


def _scan_text(label: str, text: str, terms: list[str]) -> list[tuple[str, str]]:
    lowered = text.lower()
    hits = []
    for term in terms:
        if term.lower() in lowered:
            hits.append((label, term))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--forbidden", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    terms = _load_terms(args.forbidden)
    session_id = urllib_parse.quote(args.session_id)
    base_url = args.base_url.rstrip("/")

    failures: list[tuple[str, str]] = []

    intelligence = _http_json(f"{base_url}/analyze/intelligence/{session_id}")
    failures.extend(_scan_text("intelligence_json", json.dumps(intelligence, ensure_ascii=False), terms))

    markdown = _http_text(f"{base_url}/analyze/prd/{session_id}?format=markdown")
    failures.extend(_scan_text("markdown_report", markdown, terms))

    for question in STANDARD_QUESTIONS:
        chat = _http_json(
            f"{base_url}/analyze/chat/{session_id}",
            method="POST",
            payload={"question": question, "include_history": True, "max_context_items": 20},
        )
        failures.extend(_scan_text(f"chat:{question}", json.dumps(chat, ensure_ascii=False), terms))

    if failures:
        print("FAIL")
        for field_name, term in failures:
            print(f"{field_name}: {term}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
