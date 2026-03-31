EXTRACTION_PROMPT = """
Extract structured observations from this report text.

TEXT:
{input_text}

Return JSON list:

[
  {{
    "area": "",
    "issue": "",
    "description": "",
    "severity_hint": "",
    "source": "{source}"
  }}
]

Rules:
- Capture every explicit observation in this chunk only.
- Keep wording factual and concise.
- Do not invent facts.
- If a field is missing, set it to "Not Available".
- Return raw JSON only. No markdown, no code fences, no explanation text.
- Do not output Python code or pseudocode.
"""

MERGE_PROMPT = """
Merge two datasets into one clean JSON list.

Inspection:
{inspection}

Thermal:
{thermal}

Tasks:
- Combine related issues from both sources.
- Remove duplicates without losing evidence.
- Keep conflicts explicit when sources disagree.
- If thermal evidence supports an inspection issue, mention it in description.
- If information is missing, use "Not Available".
- Do not invent facts.
- Return raw JSON array only.
- Do not include markdown/code fences.
- Do not output code snippets.

Return JSON list.
"""

DDR_PROMPT = """
You are a building diagnostics expert.

INPUT DATA:
{data}

IMAGES:
{images}

Generate a client-friendly DDR in Markdown with exactly these sections:

1. Property Issue Summary
2. Area-wise Observations (include image refs)
3. Probable Root Cause
4. Severity Assessment (with reasoning)
5. Recommended Actions
6. Additional Notes
7. Missing or Unclear Information

Rules:
- Use only facts from INPUT DATA and IMAGES.
- Do not invent facts.
- If information is missing, write "Not Available".
- If inspection and thermal details conflict, mention the conflict clearly.
- Use simple, non-technical language.
- Under "Area-wise Observations", for each area include relevant images only.
- Use image markdown format when available: ![label](relative/path).
- If an expected area image is missing, write "Image Not Available" for that area.
- Do not include unrelated images.
- Do not include JSON blocks or Python code in the DDR output.
"""