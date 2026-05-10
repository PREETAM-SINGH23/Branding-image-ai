"""Trim headline/body to fit on-canvas text areas (word-aware truncation, no network calls)."""


def _clip(text: str | None, max_len: int) -> str | None:
    s = (text or "").strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    cut = s[: max_len - 1].rsplit(" ", 1)[0]
    if not cut:
        return s[: max_len]
    return cut + "…"


def shorten_for_layout(
    headline: str | None,
    body: str | None,
    _canvas_width: int,
    _canvas_height: int,
) -> tuple[str | None, str | None]:
    """
    Shorten copy for wedge/banner space. Canvas size is reserved for future per-format limits.
    """
    max_head = 48
    max_body = 160
    return _clip(headline, max_head), _clip(body, max_body)
