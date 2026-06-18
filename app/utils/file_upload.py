import os
import uuid
from fastapi import UploadFile, HTTPException
from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def save_upload_file(file: UploadFile, folder: str = "misc") -> str:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="نوع الملف مش مسموح به. صور فقط (jpg, png, webp)")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="حجم الملف كبير. الحد الأقصى 5MB")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"

    upload_path = os.path.join(settings.UPLOAD_DIR, folder)
    os.makedirs(upload_path, exist_ok=True)

    file_path = os.path.join(upload_path, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return f"/{settings.UPLOAD_DIR}/{folder}/{filename}"
