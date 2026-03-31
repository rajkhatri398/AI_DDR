import streamlit as st
import os
import re
from extractor import extract_pdf
from pipeline import extract_structured, merge_data, generate_ddr
from utils import save_file, save_markdown

st.set_page_config(page_title="AI DDR Generator", layout="wide")

st.title("🏠 AI DDR Report Generator")

st.write("Upload Inspection & Thermal Reports")

inspection_file = st.file_uploader("Upload Inspection PDF", type=["pdf"])
thermal_file = st.file_uploader("Upload Thermal PDF", type=["pdf"])


def _resolve_markdown_image_path(path):
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized:
        return ""

    if os.path.isabs(normalized):
        return normalized

    if normalized.startswith("outputs/"):
        return normalized

    if normalized.startswith("images/"):
        return os.path.join("outputs", normalized).replace("\\", "/")

    return normalized


def render_ddr_markdown(ddr_text):
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    last_pos = 0

    for match in image_pattern.finditer(ddr_text):
        text_block = ddr_text[last_pos:match.start()]
        if text_block.strip():
            st.markdown(text_block)

        label = match.group(1).strip() or "DDR Image"
        image_path = _resolve_markdown_image_path(match.group(2))

        if image_path and os.path.exists(image_path):
            st.image(image_path, caption=label, use_container_width=True)
        else:
            st.markdown(f"- Image Not Available ({label})")

        last_pos = match.end()

    remaining = ddr_text[last_pos:]
    if remaining.strip():
        st.markdown(remaining)

if st.button("Generate DDR Report"):

    if inspection_file and thermal_file:

        os.makedirs("data", exist_ok=True)

        inspection_path = "data/inspection.pdf"
        thermal_path = "data/thermal.pdf"

        save_file(inspection_file, inspection_path)
        save_file(thermal_file, thermal_path)

        st.info("Extracting PDFs...")

        inspection_text, inspection_images = extract_pdf(
            inspection_path,
            "outputs/images/inspection"
        )

        thermal_text, thermal_images = extract_pdf(
            thermal_path,
            "outputs/images/thermal"
        )

        try:
            st.info("Structuring data...")

            inspection_struct = extract_structured(inspection_text, "inspection")
            thermal_struct = extract_structured(thermal_text, "thermal")

            st.info("Merging data...")

            merged = merge_data(inspection_struct, thermal_struct)

            st.info("Generating DDR...")

            ddr = generate_ddr(merged, inspection_images + thermal_images)
        except Exception as exc:
            st.error(f"Failed to generate DDR: {exc}")
            st.stop()

        save_markdown(ddr)

        st.success("DDR Generated!")

        st.subheader("📄 Final DDR Report")
        render_ddr_markdown(ddr)

    else:
        st.error("Please upload both files.")