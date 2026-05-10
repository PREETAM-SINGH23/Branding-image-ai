from __future__ import annotations

import logging
import math
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.services import ai_image, copy_shorten

if TYPE_CHECKING:
    from app.models import Dealership

logger = logging.getLogger(__name__)

FORMAT_SIZES: dict[str, tuple[int, int]] = {
    "1080x1080": (1080, 1080),
    "1080x1350": (1080, 1350),
    "1080x1920": (1080, 1920),
}

CREATIVE_TEMPLATES: frozenset[str] = frozenset(
    {
        "promo_split",
        "visit_dealer",
        "hero_band",
        "dealer_bottom",
        "dealer_left",
        "dealer_overlay",
        "dealer_minimal",
        "auto",
        "brand_overlay",
    }
)

_FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
_FONT_REG = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)
_FONT_ITALIC = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
)


def _load_font(paths: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
        p = Path(path)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _font_bold(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(_FONT_BOLD, size)


def _font_reg(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(_FONT_REG, size)


def _font_italic(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(_FONT_ITALIC, size)


def _horizontal_gradient_rgb(width: int, height: int, left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (width, 1))
    px = strip.load()
    for x in range(width):
        t = x / max(width - 1, 1)
        r = int(left[0] * (1 - t) + right[0] * t)
        g = int(left[1] * (1 - t) + right[1] * t)
        b = int(left[2] * (1 - t) + right[2] * t)
        px[x, 0] = (r, g, b)
    return strip.resize((width, height), Image.Resampling.BILINEAR)


def _parse_accent_hex(hex_str: str | None) -> tuple[int, int, int]:
    if not hex_str or not isinstance(hex_str, str):
        return (249, 115, 22)
    s = hex_str.strip()
    if not re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", s):
        return (249, 115, 22)
    h = s[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _cover_background(bg: Image.Image, target_w: int, target_h: int) -> Image.Image:
    tw, th = target_w, target_h
    bw, bh = bg.size
    scale = max(tw / bw, th / bh)
    nw, nh = int(bw * scale), int(bh * scale)
    resized = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _cover_overlay_rgba(overlay: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale + center-crop an RGBA overlay to exact output size (same geometry as ``_cover_background``)."""
    ov = overlay.convert("RGBA")
    return _cover_background(ov, target_w, target_h)


def _vertical_gradient_rgb(tw: int, th: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Full-canvas vertical gradient when no photo is provided (1×H strip scaled for speed)."""
    strip = Image.new("RGB", (1, th))
    spx = strip.load()
    for y in range(th):
        t = y / max(th - 1, 1)
        r = int(bottom[0] * (1 - t) + top[0] * t)
        g = int(bottom[1] * (1 - t) + top[1] * t)
        b = int(bottom[2] * (1 - t) + top[2] * t)
        spx[0, y] = (r, g, b)
    return strip.resize((tw, th), Image.Resampling.BILINEAR)


def _base_canvas(
    background_path: Path | None,
    tw: int,
    th: int,
    accent: tuple[int, int, int],
) -> Image.Image:
    """Optional hero photo; otherwise a soft gradient from the accent color."""
    if background_path is not None and background_path.is_file():
        bg = Image.open(background_path).convert("RGB")
        return _cover_background(bg, tw, th)
    top = (min(accent[0] + 45, 255), min(accent[1] + 35, 255), min(accent[2] + 55, 255))
    bot = (max(accent[0] - 70, 5), max(accent[1] - 55, 4), max(accent[2] - 45, 8))
    return _vertical_gradient_rgb(tw, th, top, bot)


def _build_panel_image(
    dealer: Dealership,
    target_width: int,
    panel_height_hint: int | None = None,
) -> Image.Image:
    path = resolve_dealer_panel_asset_path(dealer)
    if path and path.is_file():
        panel = Image.open(path).convert("RGBA")
        scale = target_width / panel.width
        new_h = max(1, int(panel.height * scale))
        return panel.resize((target_width, new_h), Image.Resampling.LANCZOS)

    height = panel_height_hint or max(140, int(target_width * 0.22))
    img = Image.new("RGBA", (target_width, height), (15, 23, 42, 245))
    draw = ImageDraw.Draw(img)
    title_font = _font_bold(28)
    small_font = _font_reg(18)
    pad = 20
    y = pad
    draw.text((pad, y), dealer.name, fill=(248, 250, 252, 255), font=title_font)
    y += 36
    for line in (dealer.address_line, dealer.phone, dealer.website):
        if line:
            draw.text((pad, y), line[:80], fill=(203, 213, 225, 255), font=small_font)
            y += 26
    return img


def resolve_dealer_panel_asset_path(dealer: Dealership) -> Path | None:
    """
    Resolve ``dealership.panel_image_path`` to an on-disk file.
    Paths may be relative to the ``backend/`` directory or to the project root (parent of ``backend/``).
    """
    rel = (dealer.panel_image_path or "").strip()
    if not rel:
        return None
    raw = Path(rel)
    if raw.is_absolute():
        return raw if raw.is_file() else None
    backend_root = Path(__file__).resolve().parent.parent.parent
    for base in (backend_root, backend_root.parent):
        p = (base / rel).resolve()
        if p.is_file():
            return p
    return None


def _paste_logo(base: Image.Image, logo: Image.Image, margin: int = 24) -> None:
    lw = int(base.width * 0.14)
    lh = int(logo.height * (lw / logo.width))
    logo_r = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    if logo_r.mode != "RGBA":
        logo_r = logo_r.convert("RGBA")
    x = base.width - logo_r.width - margin
    y = margin
    base.alpha_composite(logo_r, (x, y))


def _paste_logo_top_left(base: Image.Image, logo: Image.Image, margin: int = 24) -> None:
    lw = int(base.width * 0.14)
    lh = int(logo.height * (lw / logo.width))
    logo_r = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    if logo_r.mode != "RGBA":
        logo_r = logo_r.convert("RGBA")
    base.alpha_composite(logo_r, (margin, margin))


def _dark_panel_rgb(accent: tuple[int, int, int]) -> tuple[int, int, int]:
    """Deep footer/panel color derived from accent (readable white-on-dark text)."""
    return (
        max(min(int(accent[0] * 0.28 + 10), 52), 14),
        max(min(int(accent[1] * 0.32 + 12), 55), 18),
        max(min(int(accent[2] * 0.38 + 20), 78), 24),
    )


# Premium automotive UI: dark gradient panels, high-contrast type; keeps hero unobstructed.
_PREMIUM_RGB_TOP = (44, 38, 41)  # #2c2629
_PREMIUM_RGB_BOTTOM = (15, 23, 42)  # #0f172a
_TX_PREMIUM_PRIMARY = (255, 255, 255, 255)
_TX_PREMIUM_SECONDARY = (248, 250, 252, 255)
_TX_PREMIUM_MUTED = (226, 232, 240, 255)


def _lerp_rgb(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _premium_vertical_gradient_rgba(w: int, h: int) -> Image.Image:
    """Vertical gradient #2c2629 (top) → #0f172a (bottom), full opacity."""
    if h <= 0 or w <= 0:
        return Image.new("RGBA", (max(w, 1), max(h, 1)), (*_PREMIUM_RGB_BOTTOM, 255))
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = _lerp_rgb(_PREMIUM_RGB_TOP, _PREMIUM_RGB_BOTTOM, t)
    return strip.resize((w, h), Image.Resampling.BILINEAR).convert("RGBA")


def _feather_shadow_upward(canvas: Image.Image, x: int, y: int, tw: int, feather_h: int) -> None:
    """Soft shadow cast upward onto the hero (along top edge of a bottom panel)."""
    if feather_h <= 0:
        return
    layer = Image.new("RGBA", (tw, feather_h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(feather_h):
        a = int(32 * (1.0 - i / max(feather_h, 1)))
        ld.line([(0, feather_h - 1 - i), (tw, feather_h - 1 - i)], fill=(0, 0, 0, a))
    canvas.alpha_composite(layer, (x, y - feather_h))


def _feather_shadow_rightward(canvas: Image.Image, x: int, y: int, h: int, feather_w: int) -> None:
    """Soft shadow along the right edge of a left panel (onto the hero)."""
    if feather_w <= 0:
        return
    layer = Image.new("RGBA", (feather_w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(feather_w):
        a = int(38 * (1.0 - i / max(feather_w, 1)))
        ld.line([(i, 0), (i, h)], fill=(0, 0, 0, a))
    canvas.alpha_composite(layer, (x, y))


def suggest_template_from_image(background_path: Path | None) -> str:
    """
    Heuristic layout picker: light top band → bottom panel; darker left than center → left panel;
    else overlay. Used when creative_template is ``auto``.
    """
    if background_path is None or not background_path.is_file():
        return "dealer_bottom"
    try:
        img = Image.open(background_path).convert("RGB")
    except OSError:
        return "dealer_bottom"
    w, h = img.size
    max_side = 320
    if w >= h:
        nw, nh = max_side, max(1, int(max_side * h / w))
    else:
        nh, nw = max_side, max(1, int(max_side * w / h))
    small = img.resize((nw, nh), Image.Resampling.BILINEAR)
    sw, sh = small.size

    def mean_luma(box: tuple[int, int, int, int]) -> float:
        crop = small.crop(box)
        px = list(crop.getdata())
        if not px:
            return 128.0
        total = 0.0
        for p in px:
            total += 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
        return total / len(px)

    top = mean_luma((0, 0, sw, int(sh * 0.22)))
    left = mean_luma((0, 0, int(sw * 0.22), sh))
    center = mean_luma((int(sw * 0.34), int(sh * 0.34), int(sw * 0.66), int(sh * 0.66)))
    if top > center + 12.0:
        return "dealer_bottom"
    if left + 8.0 < center and center > 45.0:
        return "dealer_left"
    return "dealer_overlay"


def _dealer_info_visit_block(
    draw: ImageDraw.ImageDraw,
    dealer: Dealership,
    headline: str | None,
    text_x: int,
    icon_x: int,
    y: int,
    tw: int,
    th: int,
    text_max_w: int,
    row_h: int | None = None,
) -> int:
    """Draw Visit + dealer name + address + phone + site; returns bottom y."""
    row_h = row_h or max(26, int(th * 0.038))
    visit_word = (headline or "").strip() or "Visit"
    visit_font = _font_reg(max(17, int(tw * 0.022)))
    draw.text((text_x, y), visit_word[:48], fill=_TX_PREMIUM_PRIMARY, font=visit_font)
    bb = draw.textbbox((text_x, y), visit_word[:48], font=visit_font)
    y = bb[3] + int(th * 0.014)

    name_font = _font_bold(max(28, int(tw * 0.048)))
    dname = (dealer.name or "Dealership")[:42]
    for line in _wrap_lines(dname, name_font, text_max_w, draw):
        draw.text((text_x, y), line, fill=_TX_PREMIUM_PRIMARY, font=name_font)
        bb2 = draw.textbbox((text_x, y), line, font=name_font)
        y = bb2[3] + int(th * 0.02)

    row_font = _font_reg(max(15, int(tw * 0.02)))
    addr = (dealer.address_line or "").strip()
    if "," in addr:
        a1, a2 = addr.split(",", 1)[0].strip(), addr.split(",", 1)[1].strip()
        addr_lines = [a1[:56], a2[:56]]
    else:
        wrapped = _wrap_lines(addr, row_font, int(text_max_w * 0.95), draw) if addr else []
        addr_lines = (wrapped + ["", ""])[:2]

    for line in addr_lines:
        if not line:
            continue
        iy = y + row_h // 2
        _draw_pin_icon(draw, icon_x, iy, 5)
        draw.text((text_x, y), line, fill=_TX_PREMIUM_SECONDARY, font=row_font)
        y += row_h

    phone = (dealer.phone or "").strip()
    if phone:
        iy = y + row_h // 2
        _draw_phone_icon(draw, icon_x, iy)
        draw.text((text_x, y), phone[:40], fill=_TX_PREMIUM_SECONDARY, font=row_font)
        y += row_h

    web = _pretty_website(dealer.website)
    if web:
        iy = y + row_h // 2
        _draw_globe_icon(draw, icon_x, iy)
        draw.text((text_x, y), web, fill=_TX_PREMIUM_MUTED, font=row_font)
        y += row_h
    return y


def _paste_logo_with_account_name(
    canvas: Image.Image,
    logo: Image.Image,
    account_name: str,
    margin: int,
    account_label_fill: tuple[int, int, int, int] = (12, 18, 36, 255),
) -> None:
    """Logo top-right; account name to its left (default dark type for light hero areas)."""
    base = canvas
    tw = base.width
    lw = int(tw * 0.13)
    lh = int(logo.height * (lw / logo.width))
    logo_r = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    if logo_r.mode != "RGBA":
        logo_r = logo_r.convert("RGBA")
    lx = tw - logo_r.width - margin
    ly = margin
    draw = ImageDraw.Draw(canvas)
    label = (account_name or "").strip()[:40]
    if label:
        nf = _font_bold(max(18, int(tw * 0.028)))
        bbox = draw.textbbox((0, 0), label, font=nf)
        tx = lx - (bbox[2] - bbox[0]) - int(tw * 0.02)
        ty = ly + (lh - (bbox[3] - bbox[1])) // 2 - bbox[1]
        if tx >= margin:
            draw.text((tx, ty), label, fill=account_label_fill, font=nf)
    base.alpha_composite(logo_r, (lx, ly))


def _wrap_lines(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _fit_promo_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int, end: int) -> ImageFont.ImageFont:
    for size in range(start, end - 1, -2):
        font = _font_bold(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_w:
            return font
    return _font_bold(end)


def _pretty_website(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    u = re.sub(r"^https?://", "", u, flags=re.I)
    return u.split("/")[0][:48]


def _draw_pin_icon(d: ImageDraw.ImageDraw, cx: int, cy: int, s: int = 5) -> None:
    d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=(255, 255, 255, 255))
    d.line([(cx, cy + s), (cx, cy + s + 4)], fill=(255, 255, 255, 255), width=2)


def _draw_phone_icon(d: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    d.rounded_rectangle([cx - 5, cy - 6, cx + 5, cy + 6], radius=2, outline=(255, 255, 255, 255), width=2)


def _draw_globe_icon(d: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    r = 5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 255), width=2)
    d.line([(cx - r + 1, cy), (cx + r - 1, cy)], fill=(255, 255, 255, 255), width=1)


def _draw_cta_pills(
    canvas: Image.Image,
    dealer: Dealership,
    tw: int,
    th: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    pill_h = max(44, int(th * 0.055))
    radius = int(pill_h * 0.48)
    margin_x = int(tw * 0.04)
    bottom = int(th * 0.045)
    y1 = th - bottom - pill_h
    w_left = int(tw * 0.44)
    w_right = tw - margin_x * 2 - w_left - int(tw * 0.04)
    x_left = margin_x
    x_right = x_left + w_left + int(tw * 0.04)

    phone = (dealer.phone or "").strip() or "—"
    phone_display = phone[:28]

    draw.rounded_rectangle([x_left, y1, x_left + w_left, y1 + pill_h], radius=radius, fill=(255, 255, 255, 255))
    draw.rounded_rectangle([x_right, y1, x_right + w_right, y1 + pill_h], radius=radius, fill=(0, 0, 0, 255))

    small = _font_reg(max(16, int(pill_h * 0.38)))
    cta = _font_bold(max(14, int(pill_h * 0.34)))
    left_txt = f"\u260e {phone_display}"
    bbox_l = draw.textbbox((0, 0), left_txt, font=small)
    tx = x_left + (w_left - (bbox_l[2] - bbox_l[0])) // 2
    ty = y1 + (pill_h - (bbox_l[3] - bbox_l[1])) // 2 - bbox_l[1]
    draw.text((tx, ty), left_txt, fill=(15, 23, 42, 255), font=small)

    cta_txt = "CONTACT US"
    bbox_c = draw.textbbox((0, 0), cta_txt, font=cta)
    cx = x_right + (w_right - (bbox_c[2] - bbox_c[0])) // 2
    cy = y1 + (pill_h - (bbox_c[3] - bbox_c[1])) // 2 - bbox_c[1]
    draw.text((cx, cy), cta_txt, fill=(255, 255, 255, 255), font=cta)


def _draw_price_badge(
    canvas: Image.Image,
    price: str,
    tw: int,
    th: int,
    cx_frac: float,
    cy_frac: float,
) -> tuple[int, int, int]:
    draw = ImageDraw.Draw(canvas)
    r = int(min(tw, int(th * 0.55)) * 0.12)
    cx, cy = int(tw * cx_frac), int(th * cy_frac)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 255))

    price_clean = (price or "$59,000").strip()
    size = max(22, int(r * 0.42))
    font = _font_bold(size)
    bbox = draw.textbbox((0, 0), price_clean, font=font)
    while bbox[2] - bbox[0] > r * 1.65 and size > 14:
        size -= 2
        font = _font_bold(size)
        bbox = draw.textbbox((0, 0), price_clean, font=font)

    tx = cx - (bbox[2] - bbox[0]) // 2
    ty = cy - (bbox[3] - bbox[1]) // 2 - bbox[1]
    draw.text((tx, ty), price_clean, fill=(255, 255, 255, 255), font=font)
    return cx, cy, r


def _draw_brand_pill(
    canvas: Image.Image,
    label: str,
    x: int,
    y: int,
    max_w: int,
    pill_h: int,
) -> int:
    draw = ImageDraw.Draw(canvas)
    text = (label or "BRAND").strip().upper()[:22]
    small = _font_bold(max(16, int(pill_h * 0.45)))
    bbox = draw.textbbox((0, 0), text, font=small)
    pad_x = int(pill_h * 0.55)
    w = min(max_w, bbox[2] - bbox[0] + pad_x * 2)
    radius = int(pill_h * 0.45)
    draw.rounded_rectangle([x, y, x + w, y + pill_h], radius=radius, fill=(255, 255, 255, 255))
    tx = x + (w - (bbox[2] - bbox[0])) // 2
    ty = y + (pill_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((tx, ty), text, fill=(15, 23, 42, 255), font=small)
    return y + pill_h + int(pill_h * 0.35)


def _compose_promo_split(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    format_key: str,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    body: str | None,
    account_name: str,
    promo_word: str | None,
    price_display: str | None,
    accent_hex: str | None,
) -> Image.Image:
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    accent = _parse_accent_hex(accent_hex)
    wedge = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    wdraw = ImageDraw.Draw(wedge)
    wdraw.polygon([(0, 0), (tw, 0), (0, th)], fill=(*accent, 255))
    canvas.alpha_composite(wedge)

    if th >= int(tw * 1.65):
        price_cx_f, price_cy_f = 0.82, 0.22
    elif th > tw:
        price_cx_f, price_cy_f = 0.8, 0.3
    else:
        price_cx_f, price_cy_f = 0.76, 0.36

    scale = min(tw, th) / 1080.0
    if th > tw:
        scale = max(scale, min(1.28, (th / tw) ** 0.35))
    bottom_reserve = int(th * 0.14)
    safe_bottom = th - bottom_reserve
    side_margin = int(tw * 0.055)
    text_max_w = int(tw * 0.48)

    adj_h, adj_b = copy_shorten.shorten_for_layout(headline, body, tw, th)

    draw = ImageDraw.Draw(canvas)
    y = int(th * 0.055)

    small_line = (adj_h or "New car for").strip()
    head_font = _font_reg(max(22, int(28 * scale)))
    for line in _wrap_lines(small_line, head_font, text_max_w, draw):
        if y + 40 > safe_bottom:
            break
        draw.text((side_margin, y), line, fill=(255, 255, 255, 255), font=head_font)
        bb = draw.textbbox((side_margin, y), line, font=head_font)
        y += bb[3] - bb[1] + 4

    y += int(6 * scale)
    promo = (promo_word or "SALE").strip().upper()[:12]
    promo_start = max(72, int(118 * scale))
    promo_min = max(36, int(52 * scale))
    promo_font = _fit_promo_font(draw, promo, text_max_w, promo_start, promo_min)
    draw.text((side_margin, y), promo, fill=(15, 23, 42, 255), font=promo_font)
    bb = draw.textbbox((side_margin, y), promo, font=promo_font)
    y = bb[3] + int(10 * scale)

    body_font = _font_reg(max(15, int(18 * scale)))
    if adj_b:
        for line in _wrap_lines(adj_b.strip(), body_font, text_max_w, draw):
            if y + 28 > safe_bottom - int(th * 0.12):
                break
            draw.text((side_margin, y), line, fill=(255, 255, 255, 255), font=body_font)
            bb2 = draw.textbbox((side_margin, y), line, font=body_font)
            y += bb2[3] - bb2[1] + 3

    pill_h = max(36, int(42 * scale))
    y_brand = max(y + int(8 * scale), int(th * 0.36))
    _r_est = int(min(tw, int(th * 0.55)) * 0.12)
    _cy_est = int(th * price_cy_f)
    overlap_floor = _cy_est + _r_est + int(12 * scale)
    if y_brand + pill_h > overlap_floor:
        y_brand = max(int(th * 0.34), overlap_floor - pill_h - int(8 * scale))
    if y_brand + pill_h > safe_bottom - int(th * 0.02):
        y_brand = max(int(th * 0.32), safe_bottom - int(th * 0.14) - pill_h)
    _draw_brand_pill(canvas, account_name, side_margin, y_brand, int(tw * 0.52), pill_h)

    _draw_price_badge(canvas, price_display or "$59,000", tw, th, price_cx_f, price_cy_f)
    _draw_cta_pills(canvas, dealer, tw, th)

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo(canvas, lg)

    return canvas.convert("RGB")


def _compose_visit_dealer(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    account_name: str,
) -> Image.Image:
    """Diagonal navy footer with Visit + dealer info; optional logo + account name top-right."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    R = min(int(tw * 0.042), 52)
    h_l = int(th * 0.56)
    h_r = int(th * 0.66)
    navy = (18, 28, 52, 255)
    pts: list[tuple[float, float]] = [(0, th), (0, h_l), (tw, h_r), (tw, th - R)]
    for i in range(1, 10):
        theta = -(math.pi / 2) * (i / 9)
        pts.append((tw - R + R * math.cos(theta), th - R + R * math.sin(theta)))
    pts.append((0, th))
    draw.polygon(pts, fill=navy)

    pad_x = int(tw * 0.065)
    icon_x = pad_x + 8
    text_x = pad_x + int(tw * 0.055)
    y0 = h_r + int(th * 0.028)
    y = y0

    visit_word = (headline or "").strip() or "Visit"
    visit_font = _font_reg(max(17, int(tw * 0.022)))
    draw.text((text_x, y), visit_word[:48], fill=(255, 255, 255, 255), font=visit_font)
    bb = draw.textbbox((text_x, y), visit_word[:48], font=visit_font)
    y = bb[3] + int(th * 0.012)

    name_font = _font_bold(max(28, int(tw * 0.048)))
    dname = (dealer.name or "Dealership")[:42]
    for line in _wrap_lines(dname, name_font, int(tw * 0.82), draw):
        draw.text((text_x, y), line, fill=(255, 255, 255, 255), font=name_font)
        bb2 = draw.textbbox((text_x, y), line, font=name_font)
        y = bb2[3] + int(th * 0.018)

    row_font = _font_reg(max(15, int(tw * 0.02)))
    addr = (dealer.address_line or "").strip()
    if "," in addr:
        a1, a2 = addr.split(",", 1)[0].strip(), addr.split(",", 1)[1].strip()
        addr_lines = [a1[:56], a2[:56]]
    else:
        wrapped = _wrap_lines(addr, row_font, int(tw * 0.78), draw) if addr else []
        addr_lines = (wrapped + ["", ""])[:2]

    row_h = max(26, int(th * 0.038))
    for line in addr_lines:
        if not line:
            continue
        iy = y + row_h // 2
        _draw_pin_icon(draw, icon_x, iy, 5)
        draw.text((text_x, y), line, fill=(248, 250, 252, 255), font=row_font)
        y += row_h

    phone = (dealer.phone or "").strip()
    if phone:
        iy = y + row_h // 2
        _draw_phone_icon(draw, icon_x, iy)
        draw.text((text_x, y), phone[:40], fill=(248, 250, 252, 255), font=row_font)
        y += row_h

    web = _pretty_website(dealer.website)
    if web:
        iy = y + row_h // 2
        _draw_globe_icon(draw, icon_x, iy)
        draw.text((text_x, y), web, fill=(248, 250, 252, 255), font=row_font)

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo_with_account_name(canvas, lg, account_name, margin=24)
    elif account_name:
        nf = _font_bold(max(20, int(tw * 0.026)))
        bbox = draw.textbbox((0, 0), account_name[:36], font=nf)
        draw.text((tw - bbox[2] + bbox[0] - int(tw * 0.04), int(th * 0.04)), account_name[:36], fill=(12, 18, 36, 255), font=nf)

    return canvas.convert("RGB")


def _compose_hero_band(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    body: str | None,
    account_name: str,
    accent_hex: str | None,
) -> Image.Image:
    """Reference-style: solid top banner, hero, three-column footer with gradients + curved dealer panel."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    accent = _parse_accent_hex(accent_hex)
    draw = ImageDraw.Draw(canvas)

    band_h = int(th * 0.092)
    draw.rectangle([0, 0, tw, band_h], fill=(*accent, 255))

    banner = ((headline or "").strip() or "CAR BUYING REDEFINED")[:62]
    adj_h, _ = copy_shorten.shorten_for_layout(banner, None, tw, th)
    banner_txt = ((adj_h or banner).strip() or "CAR BUYING REDEFINED").upper()[:62]
    bf = _font_bold(max(17, int(tw * 0.028)))
    bb = draw.textbbox((0, 0), banner_txt, font=bf)
    tx = (tw - (bb[2] - bb[0])) // 2
    ty = (band_h - (bb[3] - bb[1])) // 2 - bb[1]
    draw.text((max(int(tw * 0.04), tx), ty), banner_txt, fill=(255, 255, 255, 255), font=bf)

    foot_h = int(th * 0.215)
    fy = th - foot_h
    w1 = int(tw * 0.33)
    w2 = int(tw * 0.34)
    w3 = tw - w1 - w2
    x1, x2 = 0, w1
    x_mid = w1 + w2

    maroon_l = (max(accent[0] - 55, 25), max(accent[1] - 45, 15), max(accent[2] - 35, 20))
    maroon_r = (max(accent[0] - 25, 45), max(accent[1] - 20, 35), max(accent[2] - 15, 30))
    mid_l = (min(accent[0] + 55, 255), min(accent[1] + 35, 255), min(accent[2] + 30, 255))
    mid_r = accent
    gray_bg = (232, 233, 237)

    draw.rectangle([0, fy, tw, th], fill=(*gray_bg, 255))

    left_grad = _horizontal_gradient_rgb(w1, foot_h, maroon_l, maroon_r).convert("RGBA")
    canvas.alpha_composite(left_grad, (x1, fy))

    mid_grad = _horizontal_gradient_rgb(w2, foot_h, mid_l, mid_r).convert("RGBA")
    canvas.alpha_composite(mid_grad, (x2, fy))

    small = _font_reg(max(13, int(tw * 0.019)))
    bold = _font_bold(max(15, int(tw * 0.022)))
    it = _font_italic(max(13, int(tw * 0.019)))
    pad = int(tw * 0.038)
    site = _pretty_website(dealer.website) or "www.yourdomain.com"
    draw.text((x1 + pad, fy + int(foot_h * 0.38)), site.lower(), fill=(255, 255, 255, 255), font=small)

    draw.text((x2 + pad, fy + int(foot_h * 0.2)), "Call or Text", fill=(255, 255, 255, 245), font=it)
    ph = (dealer.phone or "—")[:24]
    draw.text((x2 + pad, fy + int(foot_h * 0.46)), ph, fill=(255, 255, 255, 255), font=bold)

    ix = x_mid + pad + int(w3 * 0.06)
    iy = fy + int(foot_h * 0.12)
    car_pts = [(ix, iy + 10), (ix + 16, iy), (ix + 32, iy + 8), (ix + 26, iy + 18), (ix + 8, iy + 16)]
    draw.polygon(car_pts, fill=(*accent, 255))

    dname = (dealer.name or "COMPANY NAME")[:34].upper()
    nb = _font_bold(max(14, int(tw * 0.021)))
    draw.text((x_mid + pad, fy + int(foot_h * 0.34)), dname, fill=(*accent, 255), font=nb)

    addr_small = _font_reg(max(12, int(tw * 0.017)))
    addr_short = (dealer.address_line or "")[:52]
    ay = fy + int(foot_h * 0.52)
    if addr_short:
        for i, ln in enumerate(_wrap_lines(addr_short, addr_small, w3 - 2 * pad, draw)[:2]):
            draw.text((x_mid + pad, ay + i * int(foot_h * 0.17)), ln, fill=(38, 40, 46, 255), font=addr_small)

    tag = ((body or "").strip() or "The hassle-free way to shop your next vehicle.")[:120]
    tf = _font_reg(max(14, int(tw * 0.02)))
    ty0 = band_h + int((fy - band_h) * 0.7)
    for i, ln in enumerate(_wrap_lines(tag, tf, int(tw * 0.88), draw)[:3]):
        bb3 = draw.textbbox((0, 0), ln, font=tf)
        draw.text(((tw - (bb3[2] - bb3[0])) // 2, ty0 + i * int(th * 0.03)), ln, fill=(255, 255, 255, 248), font=tf)

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo(canvas, lg, margin=int(tw * 0.022))

    return canvas.convert("RGB")


def _compose_dealer_bottom(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    account_name: str,
    accent_hex: str | None,
) -> Image.Image:
    """Hero car on top, premium gradient bottom panel; subtle separation from hero; logo top-right."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    panel_top = int(th * 0.58)
    panel_h = th - panel_top
    feather = max(12, int(th * 0.016))
    _feather_shadow_upward(canvas, 0, panel_top, tw, feather)
    grad = _premium_vertical_gradient_rgba(tw, panel_h)
    canvas.alpha_composite(grad, (0, panel_top))
    draw = ImageDraw.Draw(canvas)
    draw.line([(0, panel_top), (tw, panel_top)], fill=(255, 255, 255, 32), width=1)

    pad_x = int(tw * 0.065)
    icon_x = pad_x + 8
    text_x = pad_x + int(tw * 0.055)
    y0 = panel_top + int(th * 0.03)
    _dealer_info_visit_block(draw, dealer, headline, text_x, icon_x, y0, tw, th, int(tw * 0.84))

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo_with_account_name(canvas, lg, account_name, margin=24, account_label_fill=_TX_PREMIUM_PRIMARY)
    elif account_name:
        nf = _font_bold(max(20, int(tw * 0.026)))
        bbox = draw.textbbox((0, 0), account_name[:36], font=nf)
        draw.text(
            (tw - bbox[2] + bbox[0] - int(tw * 0.04), int(th * 0.042)),
            account_name[:36],
            fill=_TX_PREMIUM_PRIMARY,
            font=nf,
        )

    return canvas.convert("RGB")


def _compose_dealer_left(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    account_name: str,
    accent_hex: str | None,
) -> Image.Image:
    """Left info column with premium gradient; soft edge on hero; logo top-left."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    w_panel = int(tw * 0.38)
    edge_feather = max(10, int(tw * 0.014))
    _feather_shadow_rightward(canvas, w_panel, 0, th, edge_feather)
    grad = _premium_vertical_gradient_rgba(w_panel, th)
    canvas.alpha_composite(grad, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.line([(w_panel, 0), (w_panel, th)], fill=(255, 255, 255, 26), width=1)

    pad_x = int(w_panel * 0.08)
    icon_x = pad_x + 6
    text_x = pad_x + int(w_panel * 0.12)
    y0 = int(th * 0.09)
    max_w = w_panel - pad_x * 2
    _dealer_info_visit_block(draw, dealer, headline, text_x, icon_x, y0, tw, th, max_w)

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo_top_left(canvas, lg, margin=int(tw * 0.028))
    elif account_name:
        nf = _font_bold(max(18, int(tw * 0.024)))
        draw.text((int(tw * 0.04), int(th * 0.04)), account_name[:36], fill=_TX_PREMIUM_PRIMARY, font=nf)

    return canvas.convert("RGB")


def _compose_dealer_overlay(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    account_name: str,
    accent_hex: str | None,
) -> Image.Image:
    """Full-bleed hero; premium gradient wash over bottom band (car stays visible toward top of band)."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    band_h = int(th * 0.32)
    feather = max(10, int(th * 0.014))
    _feather_shadow_upward(canvas, 0, th - band_h, tw, feather)
    overlay = Image.new("RGBA", (tw, band_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for yy in range(band_h):
        bt = yy / max(band_h - 1, 1)
        r, g, b = _lerp_rgb(_PREMIUM_RGB_TOP, _PREMIUM_RGB_BOTTOM, bt)
        a = int(55 + bt * 165)
        od.line([(0, yy), (tw, yy)], fill=(r, g, b, a))
    canvas.alpha_composite(overlay, (0, th - band_h))

    draw = ImageDraw.Draw(canvas)
    draw.line([(0, th - band_h), (tw, th - band_h)], fill=(255, 255, 255, 28), width=1)
    pad_x = int(tw * 0.065)
    icon_x = pad_x + 8
    text_x = pad_x + int(tw * 0.055)
    y0 = th - band_h + int(th * 0.03)
    _dealer_info_visit_block(draw, dealer, headline, text_x, icon_x, y0, tw, th, int(tw * 0.84))

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo_with_account_name(canvas, lg, account_name, margin=24, account_label_fill=_TX_PREMIUM_PRIMARY)
    elif account_name:
        nf = _font_bold(max(20, int(tw * 0.026)))
        bbox = draw.textbbox((0, 0), account_name[:36], font=nf)
        draw.text(
            (tw - bbox[2] + bbox[0] - int(tw * 0.04), int(th * 0.042)),
            account_name[:36],
            fill=_TX_PREMIUM_PRIMARY,
            font=nf,
        )

    return canvas.convert("RGB")


def _compose_dealer_minimal(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    account_name: str,
) -> Image.Image:
    """Centered hero; slim gradient CTA strip with clear white type."""
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    strip_h = max(int(th * 0.082), 70)
    sy = th - strip_h
    feather = max(8, int(th * 0.012))
    _feather_shadow_upward(canvas, 0, sy, tw, feather)
    strip = _premium_vertical_gradient_rgba(tw, strip_h)
    canvas.alpha_composite(strip, (0, sy))
    draw = ImageDraw.Draw(canvas)
    draw.line([(0, sy), (tw, sy)], fill=(255, 255, 255, 30), width=1)

    phone = (dealer.phone or "").strip() or "—"
    cta = ((headline or "").strip() or "SCHEDULE YOUR VISIT")[:44].upper()
    small = _font_reg(max(14, int(tw * 0.021)))
    bold = _font_bold(max(16, int(tw * 0.023)))
    pad = int(tw * 0.052)
    mid_y = sy + strip_h // 2
    draw.text((pad, mid_y - 20), phone[:32], fill=_TX_PREMIUM_PRIMARY, font=bold)
    bb_c = draw.textbbox((0, 0), cta, font=small)
    draw.text((tw - pad - (bb_c[2] - bb_c[0]), mid_y - 17), cta, fill=_TX_PREMIUM_MUTED, font=small)

    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo_with_account_name(canvas, lg, account_name, margin=24, account_label_fill=_TX_PREMIUM_PRIMARY)
    elif account_name:
        nf = _font_bold(max(18, int(tw * 0.024)))
        bbox = draw.textbbox((0, 0), account_name[:36], font=nf)
        draw.text(
            (tw - bbox[2] + bbox[0] - int(tw * 0.04), int(th * 0.042)),
            account_name[:36],
            fill=_TX_PREMIUM_PRIMARY,
            font=nf,
        )

    return canvas.convert("RGB")


def _compose_brand_overlay(
    canvas_rgb: Image.Image,
    dealer: Dealership,
    logo_path: Path | None,
    logo_enabled: bool,
    extra_assets_enabled: bool,
) -> Image.Image:
    """
    Full-bleed hero or gradient, then a dealership ``template.png`` frame (transparent hero window + branded footer),
    matching the packaged creatives under ``assets/Dealership-panels/``. Requires **Enable additional assets** and
    ``panel_image_path`` on the dealership row.
    """
    tw, th = canvas_rgb.size
    canvas = canvas_rgb.convert("RGBA")
    if extra_assets_enabled:
        p = resolve_dealer_panel_asset_path(dealer)
        if p and p.suffix.lower() == ".png":
            try:
                ov = Image.open(p).convert("RGBA")
                ov2 = _cover_overlay_rgba(ov, tw, th)
                canvas.alpha_composite(ov2, (0, 0))
            except OSError as e:
                logger.warning("brand_overlay could not load panel %s: %s", p, e)
        elif not p:
            logger.info(
                "brand_overlay: extra assets on but no resolvable panel_image_path for dealer_id=%s code=%r",
                getattr(dealer, "id", None),
                getattr(dealer, "code", None),
            )
        else:
            logger.info("brand_overlay: panel path is not a PNG (need alpha): %s", p)
    if logo_enabled and logo_path and logo_path.is_file():
        lg = Image.open(logo_path).convert("RGBA")
        _paste_logo(canvas, lg, margin=max(18, int(tw * 0.022)))
    return canvas.convert("RGB")


def compose_creative(
    background_path: Path | None,
    dealer: Dealership,
    format_key: str,
    logo_path: Path | None,
    logo_enabled: bool,
    headline: str | None,
    body: str | None,
    account_name: str,
    promo_word: str | None = None,
    price_display: str | None = None,
    accent_hex: str | None = None,
    creative_template: str = "promo_split",
    ai_generate_background: bool = False,
    extra_assets_enabled: bool = False,
) -> tuple[Image.Image, bool]:
    """
    creative_template:
      - promo_split: diagonal accent wedge + hero + price + CTAs (optional photo / gradient).
      - visit_dealer: full-bleed photo or gradient + navy diagonal footer (Visit + dealer).
      - hero_band: top slogan bar + footer bands (Mercedes-style strip layout).
      - dealer_bottom: hero on top + flat solid bottom panel (logo top-right).
      - dealer_left: left info column + image on the right (logo top-left).
      - dealer_overlay: full image + semi-transparent bottom band over hero.
      - dealer_minimal: thin bottom strip with phone + CTA line (logo top-right).
      - auto: pick dealer_bottom / dealer_left / dealer_overlay from hero image heuristics.
      - brand_overlay: hero (upload / AI / accent gradient) + semitransparent dealership PNG from ``panel_image_path``
        when ``extra_assets_enabled`` is True (packaged ``template.png`` style).
      - ai_generate_background: when True and no upload, OpenAI Images API if OPENAI_API_KEY is set; else accent gradient.
    """
    tpl_in = (creative_template or "promo_split").strip().lower()
    if tpl_in not in CREATIVE_TEMPLATES:
        tpl_in = "promo_split"

    tw, th = FORMAT_SIZES[format_key]
    accent = _parse_accent_hex(accent_hex)

    effective_bg = background_path
    temp_ai_paths: list[Path] = []
    use_upload = background_path is not None and background_path.is_file()

    if ai_generate_background and not use_upload:
        if settings.openai_api_key:
            prompt = ai_image.build_dealership_image_prompt(account_name, dealer, headline, body, tpl_in)
            gen = ai_image.generate_hero_image(tw, th, prompt)
            if gen is not None:
                tf = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                gen.save(tf.name, format="JPEG", quality=92, subsampling=0)
                tf.close()
                p = Path(tf.name)
                temp_ai_paths.append(p)
                effective_bg = p
                logger.info("compose_creative OpenAI hero image generated dealer_id=%s", getattr(dealer, "id", None))
            else:
                logger.warning(
                    "compose_creative OpenAI Images returned no image; gradient dealer_id=%s",
                    getattr(dealer, "id", None),
                )
        else:
            logger.info(
                "compose_creative AI hero not used (no OPENAI_API_KEY); gradient dealer_id=%s",
                getattr(dealer, "id", None),
            )

    tpl = tpl_in
    if tpl == "auto":
        tpl = suggest_template_from_image(effective_bg if effective_bg is not None and effective_bg.is_file() else None)
        logger.info("compose_creative auto resolved -> %s", tpl)

    used_ai_hero = len(temp_ai_paths) > 0
    base = _base_canvas(effective_bg, tw, th, accent)
    for p in temp_ai_paths:
        try:
            p.unlink()
        except OSError:
            pass

    logger.info(
        "compose_creative template=%s format=%s canvas=%sx%s dealer_id=%s code=%r bg_upload=%s ai_hero=%s",
        tpl,
        format_key,
        tw,
        th,
        getattr(dealer, "id", None),
        getattr(dealer, "code", None),
        use_upload,
        used_ai_hero,
    )

    if tpl == "visit_dealer":
        return _compose_visit_dealer(base, dealer, logo_path, logo_enabled, headline, account_name), used_ai_hero
    if tpl == "hero_band":
        return (
            _compose_hero_band(base, dealer, logo_path, logo_enabled, headline, body, account_name, accent_hex),
            used_ai_hero,
        )
    if tpl == "dealer_bottom":
        return _compose_dealer_bottom(base, dealer, logo_path, logo_enabled, headline, account_name, accent_hex), used_ai_hero
    if tpl == "dealer_left":
        return _compose_dealer_left(base, dealer, logo_path, logo_enabled, headline, account_name, accent_hex), used_ai_hero
    if tpl == "dealer_overlay":
        return _compose_dealer_overlay(base, dealer, logo_path, logo_enabled, headline, account_name, accent_hex), used_ai_hero
    if tpl == "dealer_minimal":
        return _compose_dealer_minimal(base, dealer, logo_path, logo_enabled, headline, account_name), used_ai_hero
    if tpl == "brand_overlay":
        return (
            _compose_brand_overlay(base, dealer, logo_path, logo_enabled, extra_assets_enabled),
            used_ai_hero,
        )

    return (
        _compose_promo_split(
            base,
            dealer,
            format_key,
            logo_path,
            logo_enabled,
            headline,
            body,
            account_name,
            promo_word,
            price_display,
            accent_hex,
        ),
        used_ai_hero,
    )
