"""
AHAL AI — Gemini Client (Phase 2)

Gemini API integration for Gemma 26B IT.
Explanation-only — the LLM must never detect or create new facts.
Safe — never crashes the IntelligenceEngine if the API call fails.
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib import request as urllib_request
from urllib.error import URLError

from app.config import config

logger = logging.getLogger("ahal.llm.gemini")

# Gemini REST endpoint template
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent?key={api_key}"
)


class GeminiClient:
    """
    Google Gemini API client for Gemma 26B IT explanation generation.

    Uses the REST API directly (no SDK dependency).
    Reads config from GEMINI_API_KEY, AHAL_LLM_MODEL, AHAL_LLM_TIMEOUT_SECONDS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self._api_key = api_key or config.scanner.gemini_api_key
        self._model = model or config.scanner.llm_model
        self._timeout = timeout or config.scanner.llm_timeout_seconds

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the Gemini API and return the generated text.
        Returns empty string on failure.
        """
        if not config.scanner.llm_enabled:
            logger.info("LLM disabled")
            return ""

        if not self._api_key:
            logger.warning("Gemini API key missing")
            return ""

        url = _GEMINI_URL.format(model=self._model, api_key=self._api_key)
        payload = json.dumps({
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            },
        }).encode("utf-8")

        req = urllib_request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                # Extract text from Gemini response structure
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                
                if not text:
                    logger.warning("Gemini response empty")
                else:
                    logger.info("Gemini success")
                    
                return text
        except (URLError, json.JSONDecodeError, ValueError) as e:
            logger.error("Gemini API call failed: %s", e)
            return ""
        except Exception as e:
            logger.error("Gemini API call failed unexpectedly: %s", type(e).__name__)
            return ""

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def enabled(self) -> bool:
        return config.scanner.llm_enabled and bool(self._api_key)
