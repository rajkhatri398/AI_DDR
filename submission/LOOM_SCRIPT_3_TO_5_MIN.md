# Loom Script (3-5 Minutes)

Use this speaking script as-is or customize it.

## 0:00 - 0:30 | Intro

Hi, I am [Your Name].
This project is an AI-based DDR Report Generator built with Streamlit.
It takes an inspection PDF and a thermal PDF, then produces a structured final DDR report in markdown.

## 0:30 - 1:30 | What I Built

I built a web app where the user uploads two files:

- Inspection report PDF
- Thermal report PDF

Once both are uploaded, the app processes them and generates a client-friendly DDR with:

- Property issue summary
- Area-wise observations
- Probable root cause
- Severity reasoning
- Recommended actions
- Additional notes
- Missing or unclear information

The report is shown in the UI and saved to outputs/final_ddr.md.

## 1:30 - 2:45 | How It Works

Pipeline overview:

1. PDF extraction:
   The app extracts page text and images from each PDF.

2. Structured extraction:
   Text is chunked and sent to a language model to extract normalized observations as JSON.

3. Merge step:
   Inspection and thermal observations are merged, deduplicated, and conflicts are preserved.

4. DDR generation:
   The merged evidence and image metadata are used to generate a markdown DDR in a fixed section format.

5. Reliability fallback:
   If all configured models are rate-limited, the app uses fallback logic to still generate a report with best-effort output.

## 2:45 - 3:30 | Limitations

Current limitations:

- Requires a valid Groq API key
- Performance and quality depend on model availability and rate limits
- Fallback mode is less accurate than full LLM mode
- Supports only two specific report inputs right now
- Image extraction can miss some useful small images

## 3:30 - 4:30 | Improvements

If I continue this project, I would:

- Add OCR for scanned documents
- Add confidence scores per observation
- Improve mapping between observations and images
- Add PDF/DOCX export and batch processing
- Deploy a stable public demo and add automated test coverage

## 4:30 - 5:00 | Close

Thank you for reviewing my submission.
In the shared Google Drive folder, I included the Loom link, repository link, live/demo link, screenshots, and final output files.
