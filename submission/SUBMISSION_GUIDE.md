# Submission Guide

Use this checklist to complete and submit everything in one Google Drive folder.

## 1) Required Deliverables

- Working output proof:
  - Live demo link (preferred), or
  - GitHub repository link, and
  - Screenshots of working output
- Loom video (3-5 minutes) covering:
  - What you built
  - How it works
  - Limitations
  - How you would improve it
- One Google Drive folder link containing all required items

## 2) What This Project Builds

This app generates a DDR (Defect Diagnostic Report) from two uploaded PDFs:

- Inspection report PDF
- Thermal report PDF

Processing flow:

1. Extract text and images from both PDFs
2. Convert extracted content into structured observations
3. Merge inspection and thermal findings
4. Generate a markdown DDR with area-wise observations and image references
5. Save output in outputs/final_ddr.md

## 3) Suggested Submission Folder Structure (Google Drive)

Create one folder named with your full name, then place:

- Loom Video Link.txt
- Live Demo Link.txt
- GitHub Repo Link.txt
- screenshots/
  - 01-home-page.png
  - 02-uploaded-files.png
  - 03-generation-in-progress.png
  - 04-final-ddr-view.png
  - 05-final_ddr_md-file.png
- final-output/
  - final_ddr.md
- docs/
  - limitations-and-improvements.txt

## 4) Screenshot Checklist

Capture at least these screens:

1. App landing page
2. Both PDFs uploaded
3. Generation status messages visible
4. Final DDR rendered in app
5. outputs/final_ddr.md opened in editor

## 5) Limitations You Can Mention

- Depends on external LLM API (Groq) and valid API key
- May hit model rate limits during peak usage
- Fallback mode uses heuristic extraction, which is less precise than normal model output
- Input format currently assumes two PDFs only (inspection + thermal)
- Extracted image filtering may skip small but relevant visuals

## 6) Improvements You Can Mention

- Add OCR for scanned PDFs and low-text pages
- Add confidence scoring and source traceability for each finding
- Add richer conflict detection between inspection and thermal observations
- Improve image-to-observation matching with better ranking
- Add report export options (PDF, DOCX) and batch processing
- Deploy publicly for evaluator access (Streamlit Community Cloud or Render)

## 7) Final Submit Step

Share only one Google Drive folder link that includes:

- Loom link
- Live/demo link
- GitHub repo link
- Screenshots
- Final report file
- Any supporting notes
