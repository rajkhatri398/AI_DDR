from groq import BadRequestError, Groq
import json
import os
import re
from dotenv import load_dotenv
from prompts import EXTRACTION_PROMPT, MERGE_PROMPT, DDR_PROMPT

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _truncate_text(text, max_chars):
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _safe_int_env(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _chunk_text(text, chunk_chars, overlap_chars):
    if not text:
        return []
    if chunk_chars <= 0:
        return [text]

    overlap = max(0, min(overlap_chars, chunk_chars // 2))
    step = max(1, chunk_chars - overlap)
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_chars)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def _split_page_blocks(text):
    if not text:
        return []

    # Input from extractor is formatted as repeated "Page N:\n..." blocks.
    blocks = re.split(r"(?=\bPage\s+\d+:)", text)
    return [b.strip() for b in blocks if b and b.strip()]


def _chunk_page_blocks(page_blocks, chunk_chars):
    if not page_blocks:
        return []

    if chunk_chars <= 0:
        return ["\n\n".join(page_blocks)]

    chunks = []
    current = []
    current_len = 0

    for block in page_blocks:
        block_len = len(block)
        if current and current_len + block_len > chunk_chars:
            chunks.append("\n\n".join(current))
            current = [block]
            current_len = block_len
            continue

        current.append(block)
        current_len += block_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _extract_json_array(raw_text):
    if not raw_text:
        return []

    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    parsed = None
    try:
        parsed = json.loads(cleaned)
    except Exception:
        bracket_match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
        if bracket_match:
            try:
                parsed = json.loads(bracket_match.group(0))
            except Exception:
                parsed = None

    if isinstance(parsed, list):
        return parsed
    return []


def _normalize_observation(item, source):
    if not isinstance(item, dict):
        return None

    return {
        "area": str(item.get("area", "Not Available") or "Not Available"),
        "issue": str(item.get("issue", "Not Available") or "Not Available"),
        "description": str(item.get("description", "Not Available") or "Not Available"),
        "severity_hint": str(item.get("severity_hint", "Not Available") or "Not Available"),
        "source": str(item.get("source", source) or source),
    }


def _dedupe_observations(observations):
    unique = []
    seen = set()
    for item in observations:
        key = (
            item.get("area", "").strip().lower(),
            item.get("issue", "").strip().lower(),
            item.get("description", "").strip().lower(),
            item.get("source", "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _parse_or_wrap_list(raw_text, source_label):
    parsed = _extract_json_array(raw_text)
    if parsed:
        cleaned = []
        for item in parsed:
            normalized = _normalize_observation(item, source_label)
            if normalized:
                cleaned.append(normalized)
        if cleaned:
            return cleaned

    heuristic = _heuristic_observations_from_text(raw_text, source_label)
    if heuristic:
        return heuristic

    desc = _truncate_text(str(raw_text or "Not Available"), 1200)
    if _looks_like_code(desc):
        desc = "Model returned non-JSON content. Not Available."

    return [{
        "area": "Not Available",
        "issue": "Unstructured model output",
        "description": desc,
        "severity_hint": "Not Available",
        "source": source_label,
    }]


def _get_error_details(exc):
    status_code = getattr(exc, "status_code", None)
    body = getattr(exc, "body", {}) or {}
    error = body.get("error", {}) if isinstance(body, dict) else {}
    error_code = error.get("code", "")
    message = error.get("message", str(exc))
    return status_code, error_code, message


def _is_rate_limited(status_code, error_code):
    return status_code == 429 or error_code == "rate_limit_exceeded"


def _extract_wait_hint(message):
    if not message:
        return ""
    match = re.search(r"try again in ([^\.]+)", message, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _is_all_models_rate_limited_error(exc):
    if not exc:
        return False
    text = str(exc).lower()
    return "all configured groq models are rate-limited" in text


def _get_model_candidates():
    # Override with comma-separated model names in GROQ_MODELS if needed.
    configured = os.getenv("GROQ_MODELS", "").strip()
    if configured:
        return [m.strip() for m in configured.split(",") if m.strip()]

    return [
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
        "llama-3.1-8b-instant",
    ]


def _enforce_ddr_structure(ddr_text):
    required_sections = [
        "Property Issue Summary",
        "Area-wise Observations",
        "Probable Root Cause",
        "Severity Assessment (with reasoning)",
        "Recommended Actions",
        "Additional Notes",
        "Missing or Unclear Information",
    ]

    text = (ddr_text or "").strip()
    if not text:
        text = ""

    lower_text = text.lower()
    for section in required_sections:
        if section.lower() in lower_text:
            continue
        if text:
            text += "\n\n"
        text += f"## {section}\nNot Available"

    # Ensure the missing-info section explicitly states Not Available when needed.
    missing_section_start = text.lower().find("missing or unclear information")
    if missing_section_start != -1:
        trailing = text[missing_section_start:]
        if "not available" not in trailing.lower():
            text += "\n- Not Available"

    # Ensure the area-wise section has an explicit image fallback note if model omitted it.
    area_section_start = text.lower().find("area-wise observations")
    if area_section_start != -1:
        area_trailing = text[area_section_start:]
        if "![" not in area_trailing and "image not available" not in area_trailing.lower():
            text += "\n\n- Image Not Available"

    return text


def _json_list_from_any_text(raw_text):
    items = _extract_json_array(raw_text)
    cleaned = []
    for item in items:
        normalized = _normalize_observation(item, str(item.get("source", "Not Available") if isinstance(item, dict) else "Not Available"))
        if normalized:
            cleaned.append(normalized)
    return cleaned


def _looks_like_code(text):
    content = str(text or "")
    if "import pandas" in content.lower() or "def " in content or "class " in content:
        return True
    if "```python" in content.lower() or "```" in content:
        return True
    return False


def _heuristic_observations_from_text(raw_text, source_label):
    text = str(raw_text or "").strip()
    if not text:
        return []

    # Reject obvious code-style responses so they do not pollute DDR facts.
    if _looks_like_code(text):
        return []

    max_items = _safe_int_env("HEURISTIC_MAX_ITEMS", 30)
    lines = [ln.strip(" -\t") for ln in text.splitlines() if ln.strip()]

    observations = []
    current = {
        "area": "Not Available",
        "issue": "Not Available",
        "description": "Not Available",
        "severity_hint": "Not Available",
        "source": source_label,
    }

    def flush_current():
        nonlocal current
        normalized = _normalize_observation(current, source_label)
        if normalized and (
            normalized["issue"] != "Not Available"
            or normalized["description"] != "Not Available"
        ):
            observations.append(normalized)
        current = {
            "area": "Not Available",
            "issue": "Not Available",
            "description": "Not Available",
            "severity_hint": "Not Available",
            "source": source_label,
        }

    for line in lines:
        lower = line.lower()

        if lower.startswith("area:"):
            if current["issue"] != "Not Available" or current["description"] != "Not Available":
                flush_current()
            current["area"] = line.split(":", 1)[1].strip() or "Not Available"
            continue

        if lower.startswith("issue:"):
            if current["issue"] != "Not Available" and current["description"] != "Not Available":
                flush_current()
            current["issue"] = line.split(":", 1)[1].strip() or "Not Available"
            continue

        if lower.startswith("observation:") or lower.startswith("description:"):
            current["description"] = line.split(":", 1)[1].strip() or "Not Available"
            continue

        if lower.startswith("severity"):
            current["severity_hint"] = line.split(":", 1)[1].strip() if ":" in line else "Not Available"
            if not current["severity_hint"]:
                current["severity_hint"] = "Not Available"
            continue

        # Lightweight thermal signal parser.
        temp_match = re.search(r"([A-Za-z ]+)?\s*(\d+(?:\.\d+)?)\s*°?c", line, flags=re.IGNORECASE)
        if temp_match:
            label = (temp_match.group(1) or "Temperature").strip() or "Temperature"
            value = temp_match.group(2)
            if current["issue"] == "Not Available":
                current["issue"] = "Temperature"
            if current["description"] == "Not Available":
                current["description"] = f"{label}: {value} C"
            continue

    flush_current()

    observations = _dedupe_observations(observations)
    if max_items > 0:
        observations = observations[:max_items]
    return observations


def _fallback_extract_structured(text, source):
    page_blocks = _split_page_blocks(text)
    observations = []
    limit = _safe_int_env("FALLBACK_OBS_MAX", 40)

    for block in page_blocks:
        page_match = re.search(r"Page\s+(\d+):", block)
        page_no = page_match.group(1) if page_match else "Not Available"

        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        content_lines = []
        for ln in lines:
            if re.match(r"^Page\s+\d+:$", ln):
                continue
            content_lines.append(ln)

        if not content_lines:
            continue

        snippet = " ".join(content_lines[:3])
        observations.append({
            "area": "Not Available",
            "issue": f"Observation from page {page_no}",
            "description": _truncate_text(snippet, 300),
            "severity_hint": "Not Available",
            "source": source,
        })

        if limit > 0 and len(observations) >= limit:
            break

    if not observations:
        observations = [{
            "area": "Not Available",
            "issue": "No explicit observation extracted",
            "description": "Not Available",
            "severity_hint": "Not Available",
            "source": source,
        }]

    return json.dumps(_dedupe_observations(observations), indent=2)


def _fallback_merge_data(inspection_json, thermal_json):
    inspection_items = _parse_or_wrap_list(inspection_json, "inspection")
    thermal_items = _parse_or_wrap_list(thermal_json, "thermal")

    combined = []
    for item in inspection_items + thermal_items:
        normalized = _normalize_observation(item, str(item.get("source", "Not Available") if isinstance(item, dict) else "Not Available"))
        if normalized:
            combined.append(normalized)

    return json.dumps(_dedupe_observations(combined), indent=2)


def _build_image_index(images):
    index = {}
    for img in images:
        if isinstance(img, dict):
            key_source = str(img.get("source", "")).strip().lower()
            entry = str(img.get("path", "Not Available") or "Not Available")
        else:
            key_source = ""
            entry = str(img or "Not Available")

        if key_source not in index:
            index[key_source] = []
        if entry not in index[key_source]:
            index[key_source].append(entry)
    return index


def _fallback_generate_ddr(merged_data, images):
    items = _json_list_from_any_text(merged_data)
    if not items:
        items = _parse_or_wrap_list(merged_data, "Not Available")

    items = _dedupe_observations(items)
    max_obs = _safe_int_env("FALLBACK_DDR_MAX_OBS", 60)
    if max_obs > 0:
        items = items[:max_obs]

    by_area = {}
    conflicts = []
    seen_descriptions = {}
    for item in items:
        area = item.get("area", "Not Available") or "Not Available"
        if area not in by_area:
            by_area[area] = []
        by_area[area].append(item)

        conflict_key = (
            area.strip().lower(),
            str(item.get("issue", "")).strip().lower(),
        )
        desc = str(item.get("description", "")).strip()
        prev = seen_descriptions.get(conflict_key)
        if prev and prev != desc:
            conflicts.append(f"{area}: conflicting details reported for '{item.get('issue', 'Not Available')}'.")
        elif desc:
            seen_descriptions[conflict_key] = desc

    image_index = _build_image_index(images)

    total_issues = len(items)
    area_count = len(by_area)
    summary_lines = [
        f"- Total observations identified: {total_issues}",
        f"- Areas covered: {area_count}",
    ]
    if total_issues == 0:
        summary_lines.append("- Not Available")

    area_lines = []
    for area, area_items in by_area.items():
        area_lines.append(f"### {area}")
        for obs in area_items[:8]:
            issue = obs.get("issue", "Not Available") or "Not Available"
            desc = obs.get("description", "Not Available") or "Not Available"
            sev = obs.get("severity_hint", "Not Available") or "Not Available"
            src = obs.get("source", "Not Available") or "Not Available"
            area_lines.append(f"- Issue: {issue}")
            area_lines.append(f"- Observation: {desc}")
            area_lines.append(f"- Severity Hint: {sev}")
            area_lines.append(f"- Source: {src}")

            src_key = str(src).strip().lower()
            src_images = image_index.get(src_key, [])
            if src_images:
                for img_path in src_images[:2]:
                    area_lines.append(f"![{area} - {issue}]({img_path})")
            else:
                area_lines.append("- Image Not Available")

        area_lines.append("")

    if not area_lines:
        area_lines = ["- Not Available", "- Image Not Available"]

    severity_words = " ".join(
        str(i.get("severity_hint", "")).lower() for i in items
    )
    if any(word in severity_words for word in ["critical", "high", "severe"]):
        sev_assessment = "Overall severity appears High because at least one observation is marked high/critical."
    elif any(word in severity_words for word in ["medium", "moderate"]):
        sev_assessment = "Overall severity appears Medium based on available hints across observations."
    elif total_issues > 0:
        sev_assessment = "Overall severity is Not Available due to limited explicit severity hints in the source data."
    else:
        sev_assessment = "Not Available"

    root_cause = "Not Available"
    if total_issues > 0:
        root_cause = "Likely causes include maintenance gaps, moisture ingress, material wear, or installation quality issues. Confirm with site verification."

    rec_actions = [
        "- Prioritize repairs for areas with visible damage or active faults.",
        "- Verify thermal anomalies with on-site inspection before corrective work.",
        "- Create a follow-up inspection plan after repairs.",
    ] if total_issues > 0 else ["- Not Available"]

    additional_notes = [
        "- This DDR was generated using fallback mode because AI models were temporarily rate-limited.",
        "- Findings are constrained to extracted report content only.",
    ]

    missing_info = []
    if conflicts:
        missing_info.append("- Conflicts detected:")
        seen_conflicts = set()
        for conflict in conflicts:
            text = str(conflict or "").strip()
            if not text or text in seen_conflicts:
                continue
            seen_conflicts.add(text)
            missing_info.append(f"  - {text}")
            if len(seen_conflicts) >= 8:
                break
    else:
        missing_info.append("- No explicit source conflicts detected.")

    if total_issues == 0:
        missing_info.append("- Not Available")
    else:
        missing_info.append("- Some area labels/severity values are Not Available in source documents.")

    ddr = "\n\n".join([
        "## Property Issue Summary\n" + "\n".join(summary_lines),
        "## Area-wise Observations\n" + "\n".join(area_lines),
        "## Probable Root Cause\n" + root_cause,
        "## Severity Assessment (with reasoning)\n" + sev_assessment,
        "## Recommended Actions\n" + "\n".join(rec_actions),
        "## Additional Notes\n" + "\n".join(additional_notes),
        "## Missing or Unclear Information\n" + "\n".join(missing_info),
    ])

    return _enforce_ddr_structure(ddr)


def call_llm(prompt):
    last_error = None
    rate_limit_errors = []
    for model_name in _get_model_candidates():
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as exc:
            status_code, error_code, message = _get_error_details(exc)
            if error_code == "model_decommissioned":
                last_error = exc
                continue

            if _is_rate_limited(status_code, error_code):
                wait_hint = _extract_wait_hint(message)
                hint_text = f" (retry after {wait_hint})" if wait_hint else ""
                rate_limit_errors.append(f"{model_name}{hint_text}")
                last_error = exc
                continue

            if isinstance(exc, BadRequestError):
                raise
            raise

    if rate_limit_errors:
        models_text = ", ".join(rate_limit_errors)
        raise RuntimeError(
            "All configured Groq models are rate-limited right now: "
            f"{models_text}. Reduce input size or retry after the suggested wait time."
        ) from last_error

    raise RuntimeError(
        "No working Groq model found. Update GROQ_MODELS in your .env with supported models."
    ) from last_error


def extract_structured(text, source):
    chunk_chars = _safe_int_env("EXTRACTION_CHUNK_CHARS", 7000)
    max_chunks = _safe_int_env("EXTRACTION_MAX_CHUNKS", 12)

    page_blocks = _split_page_blocks(text)
    chunks = _chunk_page_blocks(page_blocks, chunk_chars)
    if not chunks:
        chunks = _chunk_text(text, chunk_chars, 0)

    if max_chunks > 0:
        chunks = chunks[:max_chunks]

    all_observations = []
    try:
        for chunk in chunks:
            prompt = EXTRACTION_PROMPT.format(
                input_text=chunk,
                source=source,
            )
            raw = call_llm(prompt)
            all_observations.extend(_parse_or_wrap_list(raw, source))
    except Exception as exc:
        if _is_all_models_rate_limited_error(exc):
            return _fallback_extract_structured(text, source)
        raise

    all_observations = _dedupe_observations(all_observations)
    return json.dumps(all_observations, indent=2)


def merge_data(inspection_json, thermal_json):
    max_items = _safe_int_env("MERGE_MAX_ITEMS", 200)
    inspection_items = _parse_or_wrap_list(inspection_json, "inspection")
    thermal_items = _parse_or_wrap_list(thermal_json, "thermal")

    if max_items > 0:
        inspection_items = inspection_items[:max_items]
        thermal_items = thermal_items[:max_items]

    prompt = MERGE_PROMPT.format(
        inspection=json.dumps(inspection_items, indent=2),
        thermal=json.dumps(thermal_items, indent=2),
    )
    try:
        raw = call_llm(prompt)
        merged_items = _parse_or_wrap_list(raw, "merged")
        return json.dumps(_dedupe_observations(merged_items), indent=2)
    except Exception as exc:
        if _is_all_models_rate_limited_error(exc):
            return _fallback_merge_data(inspection_json, thermal_json)
        raise


def generate_ddr(merged_data, images):
    max_data_chars = _safe_int_env("DDR_DATA_MAX_CHARS", 14000)
    max_images = _safe_int_env("DDR_MAX_IMAGES", 40)

    image_context = []
    for img in images[:max_images]:
        if isinstance(img, dict):
            image_context.append({
                "source": str(img.get("source", "Not Available") or "Not Available"),
                "page": img.get("page", "Not Available"),
                "file": os.path.basename(str(img.get("file", "Not Available"))),
                "path": str(img.get("path", "Not Available") or "Not Available"),
            })
        else:
            name = os.path.basename(str(img))
            image_context.append({
                "source": "Not Available",
                "page": "Not Available",
                "file": name,
                "path": name,
            })

    prompt = DDR_PROMPT.format(
        data=_truncate_text(json.dumps(_parse_or_wrap_list(merged_data, "merged"), indent=2), max_data_chars),
        images=json.dumps(image_context, indent=2)
    )
    try:
        raw_ddr = call_llm(prompt)
        return _enforce_ddr_structure(raw_ddr)
    except Exception as exc:
        if _is_all_models_rate_limited_error(exc):
            return _fallback_generate_ddr(merged_data, image_context)
        raise