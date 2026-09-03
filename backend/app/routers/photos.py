"""Photo upload — UX_SPEC.md §4.3 and §6.5.

The browser never writes to storage directly. Every file passes through
services/photos.py (type and size check, resize, WebP, metadata stripped) and
is recorded against the member who sent it, so POST /listings can verify that
each URL it is handed is that member's own upload.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DbSession

from ..config import settings
from ..db import get_db
from ..models import Upload, User
from ..schemas import PhotoOut
from ..security import current_user
from ..services import photos

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Accepts one JPG, PNG or WebP up to MAX_PHOTO_BYTES. Returns the URL to
    put in `photo_urls` when posting."""
    data = await file.read(settings.max_photo_bytes + 1)
    try:
        processed = photos.process(data)
    except photos.PhotoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    db.add(
        Upload(
            user_id=user.id,
            url=processed.url,
            width=processed.width,
            height=processed.height,
            size_bytes=processed.size_bytes,
        )
    )
    db.commit()
    return PhotoOut(url=photos.absolute_url(processed.url), width=processed.width, height=processed.height)
