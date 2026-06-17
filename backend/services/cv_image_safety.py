from __future__ import annotations

import base64
import io
import zipfile
from typing import Any, Callable, Dict, List

MIN_IMAGE_SIDE = 72
MIN_IMAGE_AREA = 8_000
MAX_IMAGES = 12


def _image_input(data: bytes, content_type: str, label: str) -> Dict[str, Any]:
    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{content_type};base64,{encoded}"},
        "label": label,
    }


def extract_cv_images(filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
    lower_filename = (filename or "").lower()
    if lower_filename.endswith(".pdf"):
        return _extract_pdf_images(file_bytes)
    if lower_filename.endswith(".docx"):
        return _extract_docx_images(file_bytes)
    return []


def _extract_pdf_images(file_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        import fitz

        document = fitz.open(stream=file_bytes, filetype="pdf")
        images: List[Dict[str, Any]] = []
        seen_xrefs = set()
        for page_number, page in enumerate(document, start=1):
            for image_info in page.get_images(full=True):
                xref = image_info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                extracted = document.extract_image(xref)
                width = int(extracted.get("width") or 0)
                height = int(extracted.get("height") or 0)
                if min(width, height) < MIN_IMAGE_SIDE or width * height < MIN_IMAGE_AREA:
                    continue
                extension = str(extracted.get("ext") or "png").lower()
                content_type = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                }.get(extension)
                if not content_type:
                    continue
                images.append(
                    _image_input(
                        extracted["image"],
                        content_type,
                        f"PDF pagina {page_number}, immagine {xref}",
                    )
                )
                if len(images) >= MAX_IMAGES:
                    document.close()
                    return images
        document.close()
        return images
    except Exception as exc:
        raise ValueError(f"Impossibile estrarre le immagini dal PDF: {exc}") from exc


def _extract_docx_images(file_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        images: List[Dict[str, Any]] = []
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            media_names = sorted(
                name
                for name in archive.namelist()
                if name.lower().startswith("word/media/")
            )
            for name in media_names:
                extension = name.rsplit(".", 1)[-1].lower()
                content_type = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                }.get(extension)
                if not content_type:
                    continue
                data = archive.read(name)
                if len(data) < 2_000:
                    continue
                images.append(_image_input(data, content_type, name))
                if len(images) >= MAX_IMAGES:
                    break
        return images
    except Exception as exc:
        raise ValueError(f"Impossibile estrarre le immagini dal DOCX: {exc}") from exc


def validate_cv_images(
    filename: str,
    file_bytes: bytes,
    analyzer: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    images = extract_cv_images(filename, file_bytes)
    if not images:
        return {
            "status": "no_images",
            "image_count": 0,
            "analyzed_count": 0,
            "blocked": False,
            "blocked_categories": [],
        }

    results = []
    for image in images:
        result = analyzer(image)
        if not isinstance(result, dict):
            raise ValueError("Il provider visuale ha restituito una risposta non valida.")
        results.append(result)

    blocked_results = [result for result in results if result.get("blocked")]
    blocked_categories = sorted(
        {
            str(category)
            for result in blocked_results
            for category in result.get("categories", [])
            if str(category).strip()
        }
    )
    return {
        "status": "completed",
        "image_count": len(images),
        "analyzed_count": len(results),
        "blocked": bool(blocked_results),
        "blocked_categories": blocked_categories,
        "results": results,
    }
