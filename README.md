# AI-DDR: Defect Detection Report Generator

AI-DDR is an Applied AI workflow that converts raw property inspection documents into a structured, client-ready DDR (Detailed Diagnostic Report).

It takes:
- Inspection report PDF
- Thermal report PDF

And produces:
- A final markdown DDR with required sections
- Area-wise observations with relevant extracted images
- Explicit handling for missing/conflicting data (`Not Available`, conflict notes)

## Why This Project

This project was built for an Applied AI assignment focused on:
- Reasoning over imperfect input documents
- Merging two technical sources (inspection + thermal)
- Producing reliable, client-friendly output
- Avoiding hallucinations and unsupported facts

## Features

- PDF parsing with text + image extraction
- Structured observation extraction via LLM
- Deduplication and logical merge of inspection/thermal findings
- DDR generation in required format
- Image placement under area-wise observations
- Conflict and missing-data handling
- Fallback generation mode when model APIs are rate-limited

## Tech Stack

- Python
- Streamlit
- PyMuPDF (`fitz`)
- Groq API
- python-dotenv

## Project Structure

```text
ai-ddr-streamlit/
├── app.py                  # Streamlit UI
├── extractor.py            # PDF text/image extraction
├── pipeline.py             # LLM extraction, merge, DDR generation
├── prompts.py              # Prompt templates
├── utils.py                # File + markdown save helpers
├── requirements.txt
├── data/                   # Uploaded PDFs saved at runtime
├── outputs/
│   ├── final_ddr.md        # Final generated report
│   └── images/
│       ├── inspection/
│       └── thermal/
└── submission/             # Submission docs/templates
```

## DDR Output Format

The generated report contains:
1. Property Issue Summary
2. Area-wise Observations
3. Probable Root Cause
4. Severity Assessment (with reasoning)
5. Recommended Actions
6. Additional Notes
7. Missing or Unclear Information

## How It Works

1. Upload two PDFs in Streamlit:
   - Inspection report
   - Thermal report
2. `extractor.py` reads each PDF:
   - Extracts page text
   - Extracts relevant images (filters tiny/decorative assets)
3. `pipeline.py` runs 3 stages:
   - `extract_structured`: Convert each source into normalized observations
   - `merge_data`: Combine + deduplicate + preserve conflicts
   - `generate_ddr`: Build final markdown DDR with image references
4. `utils.py` saves final output at `outputs/final_ddr.md`

## Setup

### 1) Clone and enter project

```bash
git clone <your-repo-url>
cd ai-ddr-streamlit
```

### 2) Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Create `.env` in project root:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

Optional tuning vars (defaults are built in):

```dotenv
GROQ_MODELS=llama-3.3-70b-versatile,mixtral-8x7b-32768,llama-3.1-8b-instant
IMAGE_MIN_WIDTH=120
IMAGE_MIN_HEIGHT=120
IMAGE_MIN_BYTES=5000
EXTRACTION_CHUNK_CHARS=7000
EXTRACTION_MAX_CHUNKS=12
MERGE_MAX_ITEMS=200
DDR_DATA_MAX_CHARS=14000
DDR_MAX_IMAGES=40
```

### 5) Run the app

```bash
streamlit run app.py
```

Open the local URL shown in terminal (usually `http://localhost:8501`).

## Usage

1. Upload the Inspection PDF.
2. Upload the Thermal PDF.
3. Click **Generate DDR Report**.
4. Review report in UI.
5. Find saved output at `outputs/final_ddr.md`.

## Reliability and Guardrails

- Does not intentionally invent facts outside extracted data.
- Missing fields are set to `Not Available`.
- Conflicting details are surfaced in report notes.
- If all configured models are rate-limited, fallback logic generates a structured DDR from extracted content.

## Notes on Images

- Images are extracted from source PDFs and placed under relevant area-wise observations.
- If expected evidence is missing, report explicitly prints `Image Not Available`.
- Image links are normalized for markdown rendering in both Streamlit and saved report.

## Deployment

Best fit:
- Streamlit Community Cloud
- Render
- Railway

Vercel is generally not recommended for Streamlit apps due to runtime model mismatch (serverless vs persistent app process).

## Troubleshooting

- App fails with API/auth error:
  - Verify `GROQ_API_KEY` in `.env`
- Empty or weak extraction:
  - Check PDF text quality and scan quality
  - Adjust image thresholds (`IMAGE_MIN_*`)
- Rate-limit error:
  - Retry after cooldown
  - Configure multiple models using `GROQ_MODELS`

## Security

- Never commit `.env` or API keys.
- Keep `.env` in `.gitignore`.
- If a key is exposed, rotate it immediately from the provider dashboard.

## License

For assignment/demo use. Add your preferred license before production use.
