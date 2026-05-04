"""Gemini-backed answer client for Phase 4 chat."""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib import request as urllib_request
from urllib.error import URLError

from app.config import config

logger = logging.getLogger("ahal.chat.gemini")

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent?key={api_key}"
)


class GeminiChatClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else config.scanner.gemini_api_key
        self._model = model if model is not None else config.scanner.llm_model
        self._timeout = timeout if timeout is not None else config.scanner.llm_timeout_seconds
        self._enabled = config.scanner.llm_enabled if enabled is None else enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str) -> dict:
        if not self._enabled:
            logger.info("LLM disabled")
            return {"ok": False, "text": "", "error": "LLM disabled"}
            
        if not self._api_key:
            logger.warning("Gemini API key missing")
            return {"ok": False, "text": "", "error": "Gemini API key missing"}

        url = _GEMINI_URL.format(model=self._model, api_key=self._api_key)
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            }
        ).encode("utf-8")

        req = urllib_request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "") or ""
                
                if not text:
                    logger.warning("Gemini response empty")
                else:
                    logger.info("Gemini success")
                    
                return {"ok": True, "text": text, "error": None}
        except (URLError, json.JSONDecodeError, ValueError) as exc:
            logger.error("Gemini API call failed: %s", exc)
            return {"ok": False, "text": "", "error": f"Gemini API call failed: {exc}"}
        except Exception as exc:
            logger.error("Gemini API call failed unexpectedly: %s", type(exc).__name__)
            return {"ok": False, "text": "", "error": f"Gemini API call failed: {type(exc).__name__}"}
