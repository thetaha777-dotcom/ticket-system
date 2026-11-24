import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from PIL import Image

from app.auth.dependencies import require_organizer
from app.core.config import settings
from app.shared.exceptions import AppError
from app.users.models import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _store(name: str, content: bytes) -> str:
    folder = Path(settings.media_dir)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(content)
    return f"{settings.api_public_url}/media/{name}"


@router.post("/images")
async def upload_image(file: UploadFile, _: User = Depends(require_organizer)) -> dict:
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"The image is larger than {settings.max_upload_mb} MB", "file_too_large")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        extension = EXTENSIONS[image.format]
    except Exception as exc:
        raise AppError("Upload a JPEG, PNG or WebP image", "invalid_image") from exc
    return {"url": _store(f"{uuid.uuid4().hex}.{extension}", content)}
