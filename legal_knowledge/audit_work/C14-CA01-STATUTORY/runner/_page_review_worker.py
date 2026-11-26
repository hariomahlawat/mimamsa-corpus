"""Internal MuPDF worker for disposable candidate-render tests."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys


DPI = 150
MAX_PAGES_PER_PDF = 200
MAX_PIXELS = 12_000_000
MAX_INPUT_BYTES = 50_000_000


def render(raw, decoded_byte_limit):
    import pymupdf

    extension = Path(pymupdf._mupdf.__file__)
    renderer = {
        "binding_version": pymupdf.VersionBind,
        "engine_version": pymupdf.VersionFitz,
        "binding_sha256": hashlib.file_digest(extension.open("rb"), "sha256").hexdigest(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "architecture": platform.machine(),
    }
    pages = []
    decoded_bytes = 0
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        if doc.needs_pass or not doc.is_pdf or not 0 < doc.page_count <= MAX_PAGES_PER_PDF:
            raise ValueError("invalid or oversized PDF")
        if doc.is_repaired:
            raise ValueError("PDF required repair")
        for physical_page, page in enumerate(doc, start=1):
            viewport = tuple(page.rect)
            crop = tuple(page.cropbox)
            width, height = page.rect.width, page.rect.height
            if not all(math.isfinite(value) for value in (*viewport, *crop, width, height)):
                raise ValueError("invalid page geometry")
            scale = DPI / 72
            estimated_pixels = (math.ceil(width * scale) + 1) * (math.ceil(height * scale) + 1)
            if width <= 0 or height <= 0 or estimated_pixels > MAX_PIXELS:
                raise ValueError("page exceeds render limit")
            if estimated_pixels * 3 > decoded_byte_limit - decoded_bytes:
                raise ValueError("job decoded-byte budget reached")

            pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csRGB, alpha=False)
            decoded_bytes += pix.stride * pix.height
            if decoded_bytes > decoded_byte_limit:
                raise ValueError("job decoded-byte budget reached")
            png = pix.tobytes("png")
            filename = f"page-{physical_page:04d}.png"
            with open(filename, "xb") as image:
                image.write(png)
            pages.append({
                "physical_page": physical_page,
                "printed_page": None,
                "rotation_degrees": page.rotation,
                "crop_box_points": crop,
                "viewport_points": viewport,
                "width_pixels": pix.width,
                "height_pixels": pix.height,
                "image": filename,
                "image_sha256": hashlib.sha256(png).hexdigest(),
                "access_marking_review": "PENDING",
                "identity_or_anchor": None,
                "eligible_for_exact_anchor": False,
            })
    return {
        "renderer": renderer,
        "renderer_repaired_pdf": False,
        "physical_pages": len(pages),
        "decoded_bytes": decoded_bytes,
        "pages": pages,
    }


def main():
    if os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_AS, (768_000_000, 768_000_000))
        resource.setrlimit(resource.RLIMIT_FSIZE, (48_000_000, 48_000_000))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("PDF exceeds input size limit")
    maximum_decoded_bytes = int(sys.argv[1])
    print(json.dumps(render(raw, maximum_decoded_bytes), allow_nan=False))


if __name__ == "__main__":
    main()
