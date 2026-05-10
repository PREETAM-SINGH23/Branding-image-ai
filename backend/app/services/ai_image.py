"""Hero image generation via OpenAI Images API (e.g. dall-e-3). Requires OPENAI_API_KEY."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import httpx
from PIL import Image

from app.config import settings

if TYPE_CHECKING:
    from app.models import Dealership

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.openai_api_key)


def build_dealership_image_prompt(
    account_name: str,
    dealer: Dealership,
    headline: str | None,
    body: str | None,
    template_id: str,
) -> str:
    """Single prompt string for photorealistic dealership marketing photography."""
    bits = [
        "Professional photorealistic automotive dealership advertisement photograph, suitable as a wide marketing hero.",
        f"Brand context: {account_name}.",
        f"Dealership: {dealer.name}.",
        f"Creative layout hint: {template_id}.",
    ]
    if headline:
        bits.append(f"Mood inspired by campaign headline theme (do not render text): {headline[:200]}")
    if body:
        bits.append(f"Scene mood inspired by (do not render text): {(body or '')[:280]}")
    bits.append(
        "No legible text, letters, watermarks, or logos in the scene. "
        "Premium showroom, modern dealership exterior, or vehicle display area; cinematic lighting."
    )
    return " ".join(bits)[:3900]


def generate_hero_image(target_w: int, target_h: int, prompt: str) -> Image.Image | None:
    """Call OpenAI ``images/generations``, download image, return RGB PIL image."""
    key = settings.openai_api_key
    if not key:
        return None

    base = settings.openai_api_base.rstrip("/")
    model = settings.openai_image_model
    url = f"{base}/images/generations"

    ar = target_w / max(target_h, 1)
    if model.startswith("dall-e-3"):
        if ar >= 1.15:
            size = "1792x1024"
        elif ar <= 0.9:
            size = "1024x1792"
        else:
            size = "1024x1024"
    else:
        size = "1024x1024"

    payload: dict = {
        "model": model,
        "prompt": prompt[:4000],
        "n": 1,
        "size": size,
        "response_format": "url",
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code != 200:
                logger.warning("openai images/generations failed status=%s body=%s", r.status_code, r.text[:500])
                return None
            data = r.json()
            items = data.get("data") or []
            if not items:
                return None
            img_url = items[0].get("url")
            if not img_url:
                return None
            gr = client.get(img_url, follow_redirects=True)
            if gr.status_code != 200:
                logger.warning("openai image download failed status=%s", gr.status_code)
                return None
            return Image.open(io.BytesIO(gr.content)).convert("RGB")
    except (httpx.HTTPError, OSError, KeyError, ValueError, TypeError) as e:
        logger.warning("openai image generation error: %s", e)
        return None
