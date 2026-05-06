import sys
import logging
from app.config import config
from app.chat.llm.intent_router import ChatIntentRouter

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print(f"LLM Enabled: {config.scanner.llm_enabled}")
print(f"API Key present: {bool(config.scanner.gemini_api_key)}")
print(f"Model: {config.scanner.llm_model}")

router = ChatIntentRouter()
result = router.route("hi")
print(f"ROUTER RESULT: {result}")
