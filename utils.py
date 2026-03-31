import os
import re

def save_file(file, path):
    with open(path, "wb") as f:
        f.write(file.getbuffer())

def save_markdown(text, path="outputs/final_ddr.md"):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")

    def _normalize_image_link(match):
        label = match.group(1)
        img_path = (match.group(2) or "").strip().replace("\\", "/")

        if img_path.startswith("outputs/images/"):
            img_path = img_path.replace("outputs/images/", "images/", 1)
        elif img_path.startswith("./outputs/images/"):
            img_path = img_path.replace("./outputs/images/", "images/", 1)

        return f"![{label}]({img_path})"

    normalized = image_pattern.sub(_normalize_image_link, text or "")

    with open(path, "w", encoding="utf-8") as f:
        f.write(normalized)