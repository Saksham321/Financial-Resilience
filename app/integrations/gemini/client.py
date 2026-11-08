"""Async Gemini REST client with structured validation and explicit failure."""
from typing import TypeVar
from pydantic import BaseModel
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.integrations.providers import request

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    @property
    def is_available(self):
        return bool(settings.GEMINI_API_KEY)

    def get_status(self):
        return {"sdk": "google-genai", "model_configured": settings.GEMINI_MODEL_NAME,
                "api_key_configured": self.is_available, "client_initialized": self.is_available,
                "mode": "LIVE_API" if self.is_available else "UNCONFIGURED"}

    async def generate_structured_response(self, prompt: str, response_schema: type[T], system_instruction=None) -> T:
        if not self.is_available:
            raise ExternalServiceError("Gemini requires GEMINI_API_KEY; no generated summary is available.")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": response_schema.model_json_schema()}}
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        response = await request("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent",
                                 headers={"x-goog-api-key": settings.GEMINI_API_KEY}, json=body,
                                 timeout=settings.GEMINI_REQUEST_TIMEOUT_SECONDS, retries=settings.GEMINI_MAX_RETRIES)
        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            return response_schema.model_validate_json("".join(p.get("text", "") for p in parts))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("Gemini returned an invalid or blocked structured response.") from exc


gemini_client = GeminiClient()
