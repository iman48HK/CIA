import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.deps import get_current_user
from app.models import User
from app.schemas import AIChatRequest, AIChatResponse

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def _request_openrouter(model: str, message: str, headers: dict[str, str]) -> httpx.Response:
    system = (
        "You are CIA, the Construction Insight Agent. Give concise, practical answers "
        "about construction projects, drawings, regulations, and site management. "
        "If unsure, say so."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        return await client.post(OPENROUTER_URL, json=payload, headers=headers)


@router.post("/chat", response_model=AIChatResponse)
async def chat(body: AIChatRequest, user: User = Depends(get_current_user)):
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Set OPENROUTER_API_KEY in backend .env",
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Construction Insight Agent",
        "Content-Type": "application/json",
    }

    try:
        r = await _request_openrouter(settings.openrouter_model, body.message, headers)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {e}") from e

    # Fallback model if primary model fails.
    if r.status_code != 200 and settings.openrouter_fallback_model:
        try:
            r = await _request_openrouter(settings.openrouter_fallback_model, body.message, headers)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {e}") from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter error: {r.status_code} {r.text[:500]}",
        )

    data = r.json()
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail="Unexpected OpenRouter response") from e

    return AIChatResponse(reply=reply or "")
