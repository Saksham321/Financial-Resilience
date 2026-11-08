"""Provider boundaries. Configurable adapters use contracts in docs/INTEGRATIONS.md."""
import asyncio
import httpx
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from decimal import Decimal
from app.core.config import settings
from app.core.exceptions import ExternalServiceError


async def request(method, url, *, timeout=None, retries=None, **kwargs):
    attempts = settings.INTEGRATION_RETRIES if retries is None else retries
    async with httpx.AsyncClient(timeout=timeout or settings.INTEGRATION_TIMEOUT_SECONDS) as client:
        for attempt in range(attempts + 1):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                elif response.is_error:
                    raise ExternalServiceError(f"External service rejected request (HTTP {response.status_code}).")
                return response
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt == attempts:
                    raise ExternalServiceError("External service unavailable after bounded retries.") from exc
                await asyncio.sleep(min(2 ** attempt, 4))


async def adapter(service, path, payload, key=None):
    url = getattr(settings, f"{service}_API_URL")
    token = getattr(settings, f"{service}_API_KEY")
    if not url or not token:
        raise ExternalServiceError(f"{service}_API_URL and {service}_API_KEY must be configured.")
    headers = {"Authorization": f"Bearer {token}"}
    if key:
        headers["Idempotency-Key"] = key
    return await request("POST", url.rstrip("/") + path, headers=headers, json=payload)


class CreditDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eligible: bool = Field(strict=True)
    product: Literal["credit", "overdraft", "none"]
    reference: str = Field(min_length=1)
    approved_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)


async def underwriting(user_id, amount, key):
    response = await adapter("UNDERWRITING", "/eligibility", {"user_id": str(user_id), "amount": str(amount), "currency": "CAD"}, key)
    try:
        result = CreditDecision.model_validate(response.json())
        if result.eligible and (result.product == "none" or result.approved_amount < Decimal(str(amount))):
            raise ValueError("Insufficient approval")
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise ExternalServiceError("Underwriting response does not satisfy the eligibility contract.") from exc


async def browsing(user_id, category, at):
    response = await adapter("BROWSING", "/context", {"user_id": str(user_id), "category": category, "at": at.isoformat(), "lookback_hours": 72})
    try:
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
            raise ValueError("Invalid matches")
        from datetime import datetime, timedelta
        for match in data["matches"]:
            viewed = datetime.fromisoformat(match["viewed_at"].replace("Z", "+00:00"))
            if viewed.tzinfo is None:
                raise ValueError("Missing timezone")
            if match["category"].casefold() == category.casefold() and at - timedelta(hours=72) <= viewed <= at:
                return True
        return False
    except (ValueError, KeyError, TypeError) as exc:
        raise ExternalServiceError("Browsing API returned an invalid response.") from exc


async def speech(text, profile):
    if not settings.ELEVENLABS_API_KEY:
        raise ExternalServiceError("Audio requires ELEVENLABS_API_KEY.")
    voice = settings.ELEVENLABS_VOICE_ID if profile == "professional" else settings.ELEVENLABS_EMPATHETIC_VOICE_ID
    if not voice:
        raise ExternalServiceError("Requested voice profile is not configured.")
    response = await request("POST", f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                             params={"output_format": "mp3_44100_128"}, headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
                             json={"text": text, "model_id": settings.ELEVENLABS_MODEL_ID}, retries=0)
    if "audio/" not in response.headers.get("content-type", "") or not response.content:
        raise ExternalServiceError("Voice provider returned no valid audio.")
    return response.content


async def fetch_cpi():
    from datetime import date
    from app.engines.calculations import add_months, D
    response = await request("POST", settings.STATSCAN_API_BASE_URL.rstrip("/") + "/getBulkVectorDataByRange",
                             json={"vectorIds": [str(settings.STATSCAN_CPI_VECTOR)],
                                    "startDataPointReleaseDate": add_months(date.today(), -48).isoformat() + "T00:00",
                                    "endDataPointReleaseDate": date.today().isoformat() + "T23:59"})
    try:
        data = response.json()
        points = data[0]["object"]["vectorDataPoint"]
        rows = [(p["refPer"][:7], D(str(p["value"]))) for p in points if p.get("value") is not None]
        if not rows or any(not value.is_finite() or value <= 0 for _, value in rows):
            raise ValueError("No valid CPI observations")
        return rows
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ExternalServiceError("Statistics Canada returned invalid CPI observations.") from exc
