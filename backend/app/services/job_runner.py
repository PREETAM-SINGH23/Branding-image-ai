import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Account, CreativeJob, CreativeOutput, Dealership
from app.services.compose import (
    FORMAT_SIZES,
    compose_creative,
    resolve_dealer_panel_asset_path,
    suggest_template_from_image,
)

logger = logging.getLogger(__name__)


def _logo_paths_for_job(job: CreativeJob) -> list[Path]:
    """Resolve one or more logo files; pool order is used in cycle per render task."""
    ids: list[str] = []
    raw = (job.logo_file_ids_json or "").strip()
    if raw:
        try:
            ids = json.loads(raw)
        except json.JSONDecodeError:
            ids = []
    if not ids and job.logo_upload_path:
        ids = [job.logo_upload_path]
    paths: list[Path] = []
    for fid in ids:
        p = settings.upload_dir / Path(str(fid)).name
        if p.is_file():
            paths.append(p)
    return paths


def run_creative_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        _run_job(db, job_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Job %s failed", job_id)
        db.rollback()
        job = db.get(CreativeJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


def _run_job(db: Session, job_id: int) -> None:
    job = db.get(CreativeJob, job_id)
    if not job:
        return

    job.status = "running"
    job.error_message = None
    job.warning_message = None
    db.commit()

    dealership_ids = json.loads(job.dealership_ids_json)
    formats = json.loads(job.formats_json)
    for fmt in formats:
        if fmt not in FORMAT_SIZES:
            raise ValueError(f"Unsupported format: {fmt}")

    dealers = (
        db.query(Dealership)
        .filter(
            Dealership.id.in_(dealership_ids),
            Dealership.account_id == job.account_id,
        )
        .order_by(Dealership.id)
        .all()
    )
    if len(dealers) != len(set(dealership_ids)):
        raise ValueError("Some dealerships were not found for this account")

    account = db.get(Account, job.account_id)
    account_name = account.name if account else "Brand"

    tpl = job.creative_template or "promo_split"
    logger.info(
        "Job %s START template=%s account_id=%s brand=%r dealers_requested_ids=%s dealers_resolved=%s "
        "formats=%s tasks_total=%s bg=%s logo_enabled=%s",
        job_id,
        tpl,
        job.account_id,
        account_name,
        dealership_ids,
        [(d.id, d.code, d.name) for d in dealers],
        formats,
        len(dealers) * len(formats),
        "yes" if (job.background_path or "").strip() else "no_gradient_fallback",
        job.logo_enabled,
    )
    logger.info(
        "Job %s copy headline=%r body_len=%s promo=%r price=%r accent=%r",
        job_id,
        (job.headline or "")[:80],
        len(job.body or ""),
        job.promo_word,
        job.price_display,
        job.accent_hex,
    )

    raw_bg = (job.background_path or "").strip()
    bg_path: Path | None = None
    if raw_bg:
        bg_path = settings.upload_dir / Path(raw_bg).name
        if not bg_path.is_file():
            raise FileNotFoundError("Background image missing (upload may have been removed)")

    if tpl == "auto":
        _hint = suggest_template_from_image(bg_path)
        logger.info(
            "Job %s template=auto heuristic_preview=%s (same rule applied per output in compose_creative)",
            job_id,
            _hint,
        )

    logo_paths = _logo_paths_for_job(job)
    job.total_tasks = len(dealers) * len(formats)
    job.completed_tasks = 0
    db.commit()

    out_dir = settings.output_dir / str(job.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    logo_on = bool(job.logo_enabled and len(logo_paths) > 0)
    task_index = 0
    saw_any_ai_hero = False

    for dealer in dealers:
        for fmt in formats:
            logo_disk: Path | None = None
            if logo_on and logo_paths:
                logo_disk = logo_paths[task_index % len(logo_paths)]
            task_index += 1
            logger.info(
                "Job %s RENDER task=%s/%s dealership_id=%s code=%r name=%r format=%s logo=%s",
                job_id,
                job.completed_tasks + 1,
                job.total_tasks,
                dealer.id,
                dealer.code,
                dealer.name,
                fmt,
                logo_disk.name if logo_disk else "none",
            )
            img, used_ai = compose_creative(
                background_path=bg_path,
                dealer=dealer,
                format_key=fmt,
                logo_path=logo_disk,
                logo_enabled=logo_on,
                headline=job.headline,
                body=job.body,
                account_name=account_name,
                promo_word=job.promo_word,
                price_display=job.price_display,
                accent_hex=job.accent_hex,
                creative_template=job.creative_template or "promo_split",
                ai_generate_background=bool(job.ai_generate_background),
                extra_assets_enabled=bool(job.extra_assets_enabled),
            )
            saw_any_ai_hero = saw_any_ai_hero or used_ai
            fname = f"{dealer.code}_{fmt}.jpg"
            fpath = out_dir / fname
            img.save(fpath, format="JPEG", quality=94, subsampling=0)
            nbytes = fpath.stat().st_size
            logger.info(
                "Job %s SAVED path=%s bytes=%s img_size=%sx%s",
                job_id,
                fpath,
                nbytes,
                img.width,
                img.height,
            )

            db.add(
                CreativeOutput(
                    job_id=job.id,
                    dealership_id=dealer.id,
                    format_key=fmt,
                    file_path=str(fpath.resolve()),
                    dealership_name=dealer.name,
                )
            )
            job.completed_tasks += 1
            db.commit()

    warn: str | None = None
    if bool(job.ai_generate_background) and not raw_bg:
        if not settings.openai_api_key:
            warn = (
                "AI hero was requested but OPENAI_API_KEY is not set. "
                "Outputs use the accent gradient for the background."
            )
        elif not saw_any_ai_hero:
            warn = (
                "AI hero was requested but OpenAI did not return usable images. "
                "Outputs use the accent gradient instead."
            )

    overlay_warn: str | None = None
    tpl_job = (job.creative_template or "").strip().lower()
    if tpl_job == "brand_overlay" and bool(job.extra_assets_enabled):
        missing = [d.code for d in dealers if not resolve_dealer_panel_asset_path(d)]
        if missing:
            overlay_warn = (
                "Brand overlay: Additional assets is on but these dealers have no resolvable "
                f"panel_image_path (PNG): {', '.join(missing)}. Those outputs are hero/gradient only."
            )
    elif tpl_job == "brand_overlay" and not bool(job.extra_assets_enabled):
        if any(resolve_dealer_panel_asset_path(d) for d in dealers):
            overlay_warn = (
                "Brand overlay: at least one dealer has a panel PNG configured. "
                "Enable Additional assets to composite that template on the hero."
            )

    parts = [m for m in (warn, overlay_warn) if m]
    job.warning_message = " ".join(parts) if parts else None
    job.status = "completed"
    db.commit()
    logger.info(
        "Job %s COMPLETED outputs=%s dir=%s note=each_file_is_one_dealer_x_one_format",
        job_id,
        len(dealers) * len(formats),
        out_dir,
    )
