import io
import json
import os
import zipfile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Account, CreativeJob, CreativeOutput, Dealership, User
from app.schemas import JobCreate, JobStatus, OutputItem, ZipSelection
from app.services.compose import FORMAT_SIZES
from app.services.job_runner import run_creative_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_status(job: CreativeJob) -> JobStatus:
    total = job.total_tasks or 0
    done = job.completed_tasks or 0
    pct = 100.0 if total == 0 else round(100.0 * done / total, 1)
    return JobStatus(
        id=job.id,
        status=job.status,
        total_tasks=total,
        completed_tasks=done,
        error_message=job.error_message,
        warning_message=job.warning_message,
        progress_percent=pct,
    )


@router.post("", response_model=JobStatus, status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> JobStatus:
    account = db.get(Account, body.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    for fmt in body.formats:
        if fmt not in FORMAT_SIZES:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}")

    dealers = (
        db.query(Dealership)
        .filter(
            Dealership.account_id == body.account_id,
            Dealership.id.in_(body.dealership_ids),
        )
        .all()
    )
    if len(dealers) != len(set(body.dealership_ids)):
        raise HTTPException(status_code=400, detail="Invalid dealership selection for this account")

    planned_total = len(body.dealership_ids) * len(body.formats)
    logo_pool_json: str | None = None
    logo_primary: str | None = body.logo_file_id
    if body.logo_file_ids:
        logo_pool_json = json.dumps(body.logo_file_ids)
        logo_primary = body.logo_file_ids[0]
    elif body.logo_file_id:
        logo_pool_json = json.dumps([body.logo_file_id])

    job = CreativeJob(
        user_id=user.id,
        account_id=body.account_id,
        status="queued",
        background_path=body.background_file_id or "",
        creative_template=body.creative_template,
        logo_enabled=body.logo_enabled,
        logo_upload_path=logo_primary,
        logo_file_ids_json=logo_pool_json,
        extra_assets_enabled=body.extra_assets_enabled,
        dealership_ids_json=json.dumps(body.dealership_ids),
        formats_json=json.dumps(body.formats),
        headline=body.headline,
        body=body.body,
        promo_word=body.promo_word,
        price_display=body.price_display,
        accent_hex=body.accent_hex,
        ai_generate_background=body.ai_generate_background,
        total_tasks=planned_total,
        completed_tasks=0,
    )
    db.add(job)
    db.flush()
    db.commit()

    background_tasks.add_task(run_creative_job, job.id)
    return _job_status(job)


@router.get("/{job_id}", response_model=JobStatus)
def get_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> JobStatus:
    job = db.get(CreativeJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status(job)


@router.get("/{job_id}/outputs", response_model=list[OutputItem])
def list_outputs(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[OutputItem]:
    job = db.get(CreativeJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = db.query(CreativeOutput).filter(CreativeOutput.job_id == job_id).order_by(CreativeOutput.id).all()
    return [
        OutputItem(
            id=o.id,
            dealership_id=o.dealership_id,
            dealership_name=o.dealership_name,
            format_key=o.format_key,
            url=f"/api/jobs/{job_id}/files/{o.id}",
        )
        for o in rows
    ]


@router.get("/{job_id}/files/{output_id}")
def download_file(
    job_id: int,
    output_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    job = db.get(CreativeJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    out = db.get(CreativeOutput, output_id)
    if not out or out.job_id != job_id:
        raise HTTPException(status_code=404, detail="Output not found")
    path = out.file_path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File missing on server")
    return FileResponse(path, filename=f"{out.dealership_name}_{out.format_key}.jpg", media_type="image/jpeg")


@router.post("/{job_id}/download-zip")
def download_zip(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    body: ZipSelection = Body(default_factory=ZipSelection),
) -> StreamingResponse:
    job = db.get(CreativeJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    q = db.query(CreativeOutput).filter(CreativeOutput.job_id == job_id)
    if body and body.output_ids:
        q = q.filter(CreativeOutput.id.in_(body.output_ids))
    rows = q.order_by(CreativeOutput.id).all()
    if not rows:
        raise HTTPException(status_code=400, detail="No outputs to zip")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for o in rows:
            if os.path.isfile(o.file_path):
                arcname = f"{o.dealership_name.replace('/', '-')}_{o.format_key}.jpg"
                zf.write(o.file_path, arcname=arcname)
    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="creatives_job_{job_id}.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
