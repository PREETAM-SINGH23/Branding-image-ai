import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.deps import get_current_user
from app.models import User
from app.schemas import UploadResponse

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXT = {".jpg", ".jpeg", ".png"}


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG and PNG uploads are allowed",
        )
    return ext


async def _store_image(file: UploadFile) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = _safe_ext(file.filename)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_dir / file_id
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    dest.write_bytes(content)
    return UploadResponse(file_id=file_id, filename=file.filename)


@router.post("/background", response_model=UploadResponse)
async def upload_background(
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(get_current_user)],
) -> UploadResponse:
    return await _store_image(file)


@router.post("/logo", response_model=UploadResponse)
async def upload_logo(
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(get_current_user)],
) -> UploadResponse:
    return await _store_image(file)
