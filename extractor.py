import fitz
import os


def _safe_int_env(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

def extract_pdf(pdf_path, image_dir):
    doc = fitz.open(pdf_path)

    os.makedirs(image_dir, exist_ok=True)

    full_text = []
    image_map = []
    source_name = os.path.basename(os.path.normpath(image_dir)) or "unknown"
    seen_xrefs = set()
    min_width = _safe_int_env("IMAGE_MIN_WIDTH", 120)
    min_height = _safe_int_env("IMAGE_MIN_HEIGHT", 120)
    min_bytes = _safe_int_env("IMAGE_MIN_BYTES", 5000)

    for page_num, page in enumerate(doc):
        text = page.get_text()
        full_text.append(f"Page {page_num+1}:\n{text}")

        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            base_image = doc.extract_image(xref)

            img_bytes = base_image["image"]
            width = int(base_image.get("width", 0) or 0)
            height = int(base_image.get("height", 0) or 0)

            # Skip likely icons, separators, and decorative assets.
            if width < min_width or height < min_height or len(img_bytes) < min_bytes:
                continue

            img_name = f"page_{page_num+1}_{img_index}.png"
            img_path = os.path.join(image_dir, img_name)

            with open(img_path, "wb") as f:
                f.write(img_bytes)

            image_map.append({
                "source": source_name,
                "page": page_num + 1,
                "file": img_name,
                "path": img_path.replace("\\", "/"),
            })

    return "\n".join(full_text), image_map