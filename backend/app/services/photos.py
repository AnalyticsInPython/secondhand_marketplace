"""Photo processing — UX_SPEC.md §4.3.

Every upload goes through here before it touches disk: the type and size are
checked, the image is re-oriented, resized to at most PHOTO_MAX_EDGE_PX on its
long side, and re-encoded as WebP with **no metadata**. Phone photos carry GPS
coordinates in EXIF; because the browser never writes to storage directly, the
strip cannot be bypassed.

Files live under MEDIA_DIR and are served by the API at /media/<name>.webp.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import settings

try:  # HEIC from iPhones works when pillow-heif is installed; optional.
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:  # pragma: no cover
    HEIC_SUPPORTED = False

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"} | ({"HEIF"} if HEIC_SUPPORTED else set())


class PhotoError(ValueError):
    """The upload was refused. The message is safe to show to the user."""


@dataclass(frozen=True)
class Processed:
    filename: str
    url: str  # relative: /media/<filename>
    width: int
    height: int
    size_bytes: int


def _flatten(img: Image.Image) -> Image.Image:
    """Drop alpha onto white rather than onto black, then force RGB."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")


def process(data: bytes) -> Processed:
    if len(data) > settings.max_photo_bytes:
        mb = settings.max_photo_bytes // (1024 * 1024)
        raise PhotoError(f"That photo is over {mb} MB. Try a smaller export.")
    if not data:
        raise PhotoError("The upload was empty.")

    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoError("That file is not an image we can read. Use JPG, PNG or WebP.") from exc

    if img.format not in ALLOWED_FORMATS:
        raise PhotoError(f"{img.format or 'That format'} is not supported. Use JPG, PNG or WebP.")

    # Honour the orientation tag *before* the tag is thrown away with the EXIF.
    img = ImageOps.exif_transpose(img)
    img = _flatten(img)
    img.thumbnail((settings.photo_max_edge_px, settings.photo_max_edge_px), Image.LANCZOS)

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.webp"
    path = settings.media_dir / filename
    # No `exif=` argument: the saved file carries no metadata at all.
    img.save(path, "WEBP", quality=settings.photo_quality, method=4)

    return Processed(
        filename=filename,
        url=f"/media/{filename}",
        width=img.width,
        height=img.height,
        size_bytes=path.stat().st_size,
    )


def absolute_url(url: str | None) -> str | None:
    """Photo URLs are stored relative to the API origin and made absolute here."""
    if url is None:
        return None
    return f"{settings.public_origin}{url}" if url.startswith("/") else url
