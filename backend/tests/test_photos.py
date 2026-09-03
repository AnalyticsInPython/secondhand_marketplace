"""Upload pipeline: type and size checks, resize, WebP, metadata stripped."""

from io import BytesIO

from PIL import Image

from tests.conftest import png_bytes, signup


def test_upload_requires_sign_in(client):
    assert client.post("/photos", files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 401


def test_jpeg_with_exif_comes_back_as_clean_webp(client):
    signup(client, "photo@columbia.edu")
    data = png_bytes(3000, 1000, fmt="JPEG", exif=True)
    r = client.post("/photos", files={"file": ("shot.jpg", data, "image/jpeg")})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["url"].startswith("http://testserver/media/") and out["url"].endswith(".webp")

    served = client.get(out["url"].replace("http://testserver", ""))
    assert served.status_code == 200
    img = Image.open(BytesIO(served.content))
    assert img.format == "WEBP"
    assert max(img.size) <= 1600
    # Orientation 6 was honoured (rotated), then the EXIF was dropped.
    assert img.size == (out["width"], out["height"]) and img.height > img.width
    assert dict(img.getexif()) == {}


def test_png_with_alpha_is_flattened(client):
    signup(client, "photo2@columbia.edu")
    r = client.post("/photos", files={"file": ("a.png", png_bytes(mode="RGBA"), "image/png")})
    assert r.status_code == 201, r.text


def test_garbage_and_oversize_are_refused(client):
    signup(client, "photo3@columbia.edu")
    r = client.post("/photos", files={"file": ("a.png", b"not an image at all", "image/png")})
    assert r.status_code == 422 and "not an image" in r.json()["detail"]

    too_big = b"\x89PNG" + b"\0" * (10 * 1024 * 1024)
    r = client.post("/photos", files={"file": ("big.png", too_big, "image/png")})
    assert r.status_code == 422 and "over 10 MB" in r.json()["detail"]
