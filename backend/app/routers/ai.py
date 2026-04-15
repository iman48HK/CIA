import httpx
import json
import csv
import base64
import binascii
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    OrdinanceFile,
    Project,
    ProjectDrawingUpload,
    ProjectFileUpload,
    ProjectOrdinanceSelection,
    User,
)
from app.schemas import AIChatRequest, AIChatResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import markdown as md

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "storage" / "reports"
REPORT_BRAND_HEADER = "Construction Insight Agent"


class ProjectAIChatRequest(AIChatRequest):
    project_id: int


class ConsolidatedReportRequest(BaseModel):
    project_id: int
    user_prompts: list[str] = Field(default_factory=list, max_length=20)
    chat_history: list[dict] = Field(default_factory=list, max_length=500)
    annotation_assets: list[dict] = Field(default_factory=list, max_length=30)
    author: str | None = Field(default=None, max_length=200)


class AnnotationMarkerIn(BaseModel):
    xPct: float = Field(ge=0, le=1)
    yPct: float = Field(ge=0, le=1)
    type: str = Field(default="deficiency", max_length=20)
    note: str = Field(default="", max_length=200)


class AnnotationAssetIn(BaseModel):
    drawing_id: int
    filename: str = Field(min_length=1, max_length=255)
    image_data_url: str = Field(min_length=1, max_length=6_000_000)
    markers: list[AnnotationMarkerIn] = Field(default_factory=list, max_length=500)


class CollectedMaterialIn(BaseModel):
    id: str = Field(default="", max_length=80)
    source: str = Field(default="assistant", max_length=120)
    label: str = Field(default="Collected output", max_length=255)
    text: str = Field(min_length=1, max_length=200_000)
    created_at: str = Field(default="", max_length=80)


class ConsolidateCollectionReportRequest(BaseModel):
    project_id: int
    items: list[CollectedMaterialIn] = Field(default_factory=list, min_length=1, max_length=80)
    chat_history: list[dict] = Field(default_factory=list, max_length=500)
    annotation_assets: list[AnnotationAssetIn] = Field(default_factory=list, max_length=30)
    author: str | None = Field(default=None, max_length=200)


async def _request_openrouter(model: str, message: str, headers: dict[str, str]) -> httpx.Response:
    system = (
        "You are AI Assistant for construction projects. "
        "Return responses in clean Markdown with this structure:\n"
        "## Quick Summary\n"
        "- 2-4 concise bullets\n\n"
        "## Key Findings\n"
        "- Ordered by impact\n\n"
        "## Recommended Actions\n"
        "- Actionable next steps\n\n"
        "## References / Citations\n"
        "- Cite standards, ordinance docs, or assumptions used\n\n"
        "## Confidence\n"
        "- confidence_score: <0-100>\n"
        "- doubt_score: <0-100>\n"
        "- manual_review_reason: <why review is needed or 'None'>\n\n"
        "Rules:\n"
        "- Be concise and practical.\n"
        "- If data is missing, explicitly state assumptions.\n"
        "- Never invent citations; if unavailable, say so.\n"
        "- Use clear headings and bullet points only (no long paragraphs)."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        return await client.post(OPENROUTER_URL, json=payload, headers=headers)


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    body: ProjectAIChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Assistant interactions are project-scoped.
    project = db.query(Project).filter(Project.id == body.project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    drawing_rows = (
        db.query(ProjectDrawingUpload)
        .filter(ProjectDrawingUpload.project_id == project.id)
        .order_by(ProjectDrawingUpload.id.desc())
        .all()
    )
    if not drawing_rows:
        raise HTTPException(
            status_code=400,
            detail="Selected project must have at least one drawing before asking CIA Assistant.",
        )
    selected_ordinance_ids = [
        oid
        for (oid,) in db.query(ProjectOrdinanceSelection.ordinance_file_id)
        .filter(ProjectOrdinanceSelection.project_id == project.id)
        .all()
    ]
    if not selected_ordinance_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one ordinance document for this project before asking CIA Assistant.",
        )
    ordinance_titles = [
        title
        for (title,) in db.query(OrdinanceFile.title)
        .filter(OrdinanceFile.id.in_(selected_ordinance_ids))
        .all()
    ]
    project_file_names = [
        fname
        for (fname,) in db.query(ProjectFileUpload.filename)
        .filter(ProjectFileUpload.project_id == project.id)
        .order_by(ProjectFileUpload.id.desc())
        .all()
    ]
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Set OPENROUTER_API_KEY in backend .env",
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Construction Insight Agent",
        "Content-Type": "application/json",
    }

    try:
        scoped_message = (
            f"[Project: {project.name} | Project ID: {project.id}]\n"
            f"[Drawings: {', '.join([d.filename for d in drawing_rows])}]\n"
            f"[Selected Ordinance Docs: {', '.join(ordinance_titles)}]\n"
            f"[Optional Project Files: {', '.join(project_file_names) if project_file_names else 'None'}]\n"
            f"{body.message}"
        )
        r = await _request_openrouter(settings.openrouter_model, scoped_message, headers)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {e}") from e

    # Fallback model if primary model fails.
    if r.status_code != 200 and settings.openrouter_fallback_model:
        try:
            r = await _request_openrouter(settings.openrouter_fallback_model, scoped_message, headers)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {e}") from e

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter error: {r.status_code} {r.text[:500]}",
        )

    data = r.json()
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail="Unexpected OpenRouter response") from e

    return AIChatResponse(reply=reply or "")


def _normalize_chat_text(s: str) -> str:
    return " ".join(s.strip().split())


def _assistant_reply_after_user_message(chat_history: list[dict], user_text: str) -> str:
    """Return the assistant message immediately following the first matching user turn."""
    target = user_text.strip()
    target_norm = _normalize_chat_text(user_text)
    n = len(chat_history)
    for i, row in enumerate(chat_history):
        if str(row.get("role", "")).lower() != "user":
            continue
        ut = str(row.get("text", "")).strip()
        if ut != target and _normalize_chat_text(ut) != target_norm:
            continue
        for j in range(i + 1, n):
            role = str(chat_history[j].get("role", "")).lower()
            if role == "assistant":
                return str(chat_history[j].get("text", "")).strip()
            if role == "user":
                break
    return "No assistant reply appears after this message in the exported transcript."


_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")


def _parse_markdown_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "General"
    sections[current] = []
    for raw_line in str(markdown_text or "").splitlines():
        m = _HEADING_RE.match(raw_line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections[current].append(raw_line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _normalize_section_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[^a-z0-9\s/]", "", n)
    n = re.sub(r"\s+", " ", n)
    return n


def _merged_sections_from_collected_prompts(items: list[CollectedMaterialIn], chat_history: list[dict]) -> dict[str, str]:
    core_map = {
        "quick summary": "Quick Summary",
        "key findings": "Key Findings",
        "recommended actions": "Recommended Actions",
        "references / citations": "References / Citations",
        "references citations": "References / Citations",
    }
    core_sections: dict[str, list[str]] = {v: [] for v in core_map.values()}
    extra_sections: dict[str, list[str]] = {}
    prompt_specific: dict[str, str] = {}

    selected_prompts = [i.text.strip() for i in items if i.text.strip()]
    for idx, prompt in enumerate(selected_prompts, start=1):
        reply = _assistant_reply_after_user_message(chat_history, prompt)
        prompt_specific[f"Prompt {idx}"] = (
            f"User message:\n{prompt}\n\nAssistant reply:\n{reply}"
        )
        parsed = _parse_markdown_sections(reply)
        for heading, body in parsed.items():
            norm = _normalize_section_name(heading)
            target = core_map.get(norm)
            if target:
                core_sections[target].append(body)
            else:
                extra_sections.setdefault(heading.strip(), []).append(body)

    merged: dict[str, str] = {}
    for k in ("Quick Summary", "Key Findings", "Recommended Actions", "References / Citations"):
        joined = "\n\n".join([s for s in core_sections.get(k, []) if s.strip()]).strip()
        if joined:
            merged[k] = joined

    for heading, chunks in extra_sections.items():
        joined = "\n\n".join([s for s in chunks if s.strip()]).strip()
        if joined:
            merged[f"Additional: {heading}"] = joined

    return {**merged, **prompt_specific}


def _reference_generated_sections() -> dict:
    """Illustrative / template blocks (shown after prompt-driven sections in exports)."""
    return {
        "4.1": (
            "Space intelligence: detect rooms and labels from drawings, capture dimensions, symbols, "
            "and material callouts. Outputs feed the area and compliance summaries below."
        ),
        "4.2": (
            "Area logic: compute Gross Floor Area (GFA) versus usable/net area, reconcile boundary "
            "ambiguities, and flag where geometry or OCR confidence is low."
        ),
        "4.3": (
            "Space-type roll-up: tabulate gross_m2, usable_m2, counts, and efficiency ratios with "
            "floor-wise splits where drawings support it."
        ),
        "4.4": (
            "Dashboards: totals, distributions, and pie-chart-ready aggregates for stakeholder review "
            "(illustrative until live metrics are wired in)."
        ),
        "4.5": {
            "manual_reinspection_required": [
                {
                    "item": "North stair dimension extraction",
                    "doubt_score": 78,
                    "manual_review_reason": "Low OCR confidence on boundary text",
                }
            ]
        },
        "4.6": (
            "Corrective actions: LLM-suggested fixes tied to cited rules and drawing references "
            "(MVP placeholder until extraction pipeline is connected)."
        ),
        "4.7": (
            "Toolchain: planned LangGraph-style flow (retrieve, check, summarize, area, doubt scoring). "
            "This report section documents intent, not live tool traces."
        ),
        "compliance": {
            "status": "MVP parser output",
            "citations": [
                {"section": "HK Code Sec. 12.4", "drawing_page": "A-103"}
            ],
        },
    }


def _report_payload(
    project_id: int,
    prompts: list[str] | None = None,
    chat_history: list[dict] | None = None,
    annotation_assets: list[dict] | None = None,
) -> dict:
    chat_rows = list(chat_history or [])
    generated: dict = {}

    if prompts:
        clean_prompts = [p.strip() for p in prompts if isinstance(p, str) and p.strip()]
        if clean_prompts:
            for i, prompt in enumerate(clean_prompts, start=1):
                reply = _assistant_reply_after_user_message(chat_rows, prompt)
                generated[f"Prompt {i}"] = (
                    f"User message:\n{prompt}\n\nAssistant reply:\n{reply}"
                )

    for key, val in _reference_generated_sections().items():
        generated[key] = val

    base = {
        "project_id": project_id,
        "generated_sections": generated,
        "citations": [{"source": "HK regulation sample", "confidence": 0.76, "doubt_score": 24}],
        "annotated_preview_note": "Issue overlays should be shown in red on drawing previews.",
        "chart_metrics": {
            "title": "Review metrics (illustrative)",
            "bars": [
                {"label": "Confidence", "value": 76, "color": "#059669"},
                {"label": "Doubt / re-check", "value": 24, "color": "#d97706"},
                {"label": "Open items", "value": 12, "color": "#dc2626"},
            ],
        },
        "deficiency_annotation_samples": [
            {
                "drawing_sheet": "A-103",
                "annotation_type": "Deficiency",
                "description": "Stair width unclear at north core — verify against code min.",
                "severity": "High",
            },
            {
                "drawing_sheet": "M-201",
                "annotation_type": "Discrepancy",
                "description": "Diffuser count differs from schedule line 14.",
                "severity": "Medium",
            },
        ],
        "annotated_drawing_assets": annotation_assets or [],
        "chat_history": chat_rows,
    }
    if prompts:
        clean_prompts = [p.strip() for p in prompts if isinstance(p, str) and p.strip()]
        if clean_prompts:
            base["selected_user_prompts"] = clean_prompts
    return base


def _apply_report_metadata(payload: dict, project: Project, report_title: str, author: str | None) -> None:
    payload["report_title"] = report_title
    payload["project_name"] = project.name
    payload["author"] = (author or "").strip() or "—"
    payload["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _html_svg_bar_dashboard(chart: dict | None) -> str:
    if not chart or not chart.get("bars"):
        return ""
    title = escape(str(chart.get("title", "Metrics")))
    bars = chart["bars"]
    vals = [int(b.get("value", 0) or 0) for b in bars]
    max_v = max(vals) if vals else 1
    w = 640
    row_h = 40
    svg_h = 52 + len(bars) * row_h
    parts = [
        '<div class="dashboard">',
        f'<h2 class="section-title">{title}</h2>',
        f'<svg viewBox="0 0 {w} {svg_h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Bar chart">',
    ]
    y = 44
    for b in bars:
        label = escape(str(b.get("label", "")))
        val = int(b.get("value", 0) or 0)
        color = escape(str(b.get("color", "#059669")))
        bw = int((val / max_v) * (w - 200)) if max_v else 0
        parts.append(f'<text x="8" y="{y + 22}" font-size="14" font-weight="600" fill="#1f2937">{label}</text>')
        parts.append(f'<rect x="168" y="{y - 6}" width="{max(bw, 6)}" height="28" fill="{color}" rx="5" opacity="0.9"/>')
        parts.append(f'<text x="{176 + bw}" y="{y + 12}" font-size="13" fill="#111827">{val}</text>')
        y += row_h
    parts.append("</svg></div>")
    return "\n".join(parts)


def _generated_section_value_as_text(v: object) -> str:
    """Single-cell plain text for structured section values (JSON for nested data)."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False, indent=2)


def _section_rows_from_payload(payload: dict) -> list[list[str]]:
    return [
        [str(k), _generated_section_value_as_text(v)]
        for k, v in (payload.get("generated_sections") or {}).items()
    ]


def _pdf_table_cell_markup(text: str) -> str:
    """ReportLab Paragraph expects XML-safe text; newlines become explicit breaks."""
    return xml_escape(str(text)).replace("\n", "<br/>").replace("\r", "")


def _html_structured_section_cell_body(raw: str) -> str:
    """Rich HTML for prompt+reply blocks; plain pre for everything else."""
    sep = "\n\nAssistant reply:\n"
    if sep not in raw:
        return f'<pre class="section-value">{escape(raw)}</pre>'
    head, tail = raw.split(sep, 1)
    head_html = f'<pre class="section-value section-prompt-part">{escape(head)}</pre>'
    reply_html = md.markdown(tail.strip(), extensions=["tables", "fenced_code", "sane_lists"])
    return (
        '<div class="section-mixed">'
        f"{head_html}"
        f'<div class="section-reply-wrap"><strong class="reply-label">Assistant reply</strong>'
        f'<div class="reply section-reply-body">{reply_html}</div></div>'
        "</div>"
    )


def _html_generated_sections_table(section_rows: list[list[str]]) -> str:
    if not section_rows:
        return ""
    rows = "".join(
        "<tr>"
        f'<th scope="row" class="section-key">{escape(key)}</th>'
        f'<td class="section-cell">{_html_structured_section_cell_body(val)}</td>'
        "</tr>"
        for key, val in section_rows
    )
    return f"""
    <section class="block">
      <h2 class="section-title">Structured sections</h2>
      <table class="data-table">
        <thead><tr><th>Section</th><th>Summary / detail</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _html_annotation_table(payload: dict) -> str:
    samples = payload.get("deficiency_annotation_samples") or []
    if not samples:
        return ""
    head = "<thead><tr><th>Drawing / sheet</th><th>Type</th><th>Description</th><th>Severity</th></tr></thead>"
    body_rows = []
    for row in samples:
        body_rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('drawing_sheet', '')))}</td>"
            f"<td><span class='pill pill-{escape(str(row.get('annotation_type', '')).lower())}'>{escape(str(row.get('annotation_type', '')))}</span></td>"
            f"<td>{escape(str(row.get('description', '')))}</td>"
            f"<td>{escape(str(row.get('severity', '')))}</td>"
            "</tr>"
        )
    note = escape(str(payload.get("annotated_preview_note", "")))
    return f"""
    <section class="block">
      <h2 class="section-title">Deficiency &amp; discrepancy annotations</h2>
      <p class="lead">Mark issues on drawings with clear callouts (deficiency = red, discrepancy = amber). Example log:</p>
      <table class="data-table">{head}<tbody>{''.join(body_rows)}</tbody></table>
      <p class="muted small">{note}</p>
    </section>
    """


def _html_attached_annotations(payload: dict) -> str:
    assets = payload.get("annotated_drawing_assets") or []
    if not assets:
        return ""
    cards: list[str] = []
    for i, row in enumerate(assets, start=1):
        filename = escape(str(row.get("filename", f"Drawing {i}")))
        marker_count = len(row.get("markers") or [])
        data_url = str(row.get("image_data_url", "")).strip()
        img_html = (
            f'<img src="{escape(data_url)}" alt="{filename}" class="annotated-preview" />'
            if data_url.startswith("data:image/")
            else '<div class="muted small">Preview unavailable</div>'
        )
        cards.append(
            f"""
            <div class="annotated-card">
              <div class="annotated-head"><strong>{filename}</strong><span class="muted small">{marker_count} marker(s)</span></div>
              {img_html}
            </div>
            """.strip()
        )
    return f"""
    <section class="block">
      <h2 class="section-title">Attached annotated drawings</h2>
      <p class="lead">User-attached drawing overlays included with this report export.</p>
      <div class="annotated-grid">{''.join(cards)}</div>
    </section>
    """


def _decode_png_data_url(data_url: str) -> bytes | None:
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        return None
    encoded = data_url[len(prefix) :]
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None


def _write_report_files(report_id: str, payload: dict) -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / f"{report_id}.json"
    csv_path = REPORTS_DIR / f"{report_id}.csv"
    xlsx_path = REPORTS_DIR / f"{report_id}.xlsx"
    pdf_path = REPORTS_DIR / f"{report_id}.pdf"
    docx_path = REPORTS_DIR / f"{report_id}.docx"
    html_path = REPORTS_DIR / f"{report_id}.html"
    json_text = json.dumps(payload, indent=2)
    json_path.write_text(json_text, encoding="utf-8")

    report_title = str(payload.get("report_title") or "AI Assistant Report")
    author = str(payload.get("author") or "—")
    project_name = str(payload.get("project_name") or f"Project #{payload.get('project_id', '')}")
    generated_at = str(payload.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    chat_rows = payload.get("chat_history") or []
    text_lines = []
    for row in chat_rows:
        role = str(row.get("role", "assistant")).upper()
        created_at = str(row.get("created_at", ""))
        text = str(row.get("text", ""))
        text_lines.append(f"[{role}] {created_at}")
        text_lines.append(text)
        text_lines.append("")
    full_chat_text = "\n".join(text_lines).strip() or "No transcript included."

    chat_blocks_html: list[str] = []
    for row in chat_rows:
        role = str(row.get("role", "assistant"))
        created_at = str(row.get("created_at", ""))
        text = str(row.get("text", ""))
        if role == "assistant":
            body_html = md.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
        else:
            body_html = f"<p>{escape(text).replace(chr(10), '<br/>')}</p>"
        label = "AI Assistant" if role == "assistant" else "You"
        chat_blocks_html.append(
            f"""
            <article class="chat-item {escape(role)}">
              <div class="chat-role">{escape(label)} · {escape(created_at)}</div>
              <div class="reply">{body_html}</div>
            </article>
            """.strip()
        )

    chart_html = _html_svg_bar_dashboard(payload.get("chart_metrics"))
    section_rows = _section_rows_from_payload(payload)
    sections_html = _html_generated_sections_table(section_rows)
    ann_html = _html_annotation_table(payload)
    attached_ann_html = _html_attached_annotations(payload)

    report_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escape(REPORT_BRAND_HEADER)} — {escape(report_title)} — {escape(report_id)}</title>
  <style>
    body {{ font-family: "Segoe UI", system-ui, sans-serif; margin: 0; color: #0f172a; background: #f8fafc; line-height: 1.55; }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 32px 24px 48px; background: #fff; min-height: 100vh;
      box-shadow: 0 1px 3px rgba(15,23,42,0.08); }}
    .report-header {{ border-bottom: 2px solid #10b981; padding-bottom: 20px; margin-bottom: 28px; }}
    .report-header h1 {{ margin: 0 0 4px; font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }}
    .report-subhead {{ margin: 0 0 10px; font-size: 1.05rem; font-weight: 600; color: #334155; }}
    .meta {{ color: #64748b; font-size: 0.9rem; display: flex; flex-wrap: wrap; gap: 12px 24px; }}
    .meta strong {{ color: #334155; }}
    .section-title {{ font-size: 1.2rem; margin: 0 0 12px; color: #0f172a; border-left: 4px solid #10b981; padding-left: 10px; }}
    .lead {{ font-size: 1rem; margin: 0 0 12px; }}
    .muted {{ color: #64748b; }}
    .small {{ font-size: 0.85rem; }}
    .block {{ margin-bottom: 32px; }}
    .dashboard {{ background: #f1f5f9; border-radius: 12px; padding: 16px 20px; margin-bottom: 8px; }}
    .dashboard svg {{ width: 100%; height: auto; display: block; }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 12px 0; }}
    .data-table th, .data-table td {{ border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; vertical-align: top; }}
    .data-table thead th {{ background: #d1fae5; font-weight: 600; }}
    .data-table tbody th.section-key {{ background: #ecfdf5; font-weight: 600; width: 11rem; max-width: 32%; }}
    .data-table td.section-cell {{ width: auto; }}
    .section-value {{ margin: 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, ui-monospace, monospace; font-size: 0.82rem; line-height: 1.45; }}
    .section-mixed {{ display: flex; flex-direction: column; gap: 0.75rem; }}
    .section-prompt-part {{ max-height: 16rem; overflow: auto; background: #f8fafc; border-radius: 6px; padding: 0.5rem 0.65rem; }}
    .section-reply-wrap {{ border-left: 3px solid #10b981; padding-left: 0.75rem; }}
    .reply-label {{ display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; margin-bottom: 0.35rem; }}
    .section-reply-body {{ font-size: 0.9rem; }}
    .pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }}
    .pill-deficiency {{ background: #fee2e2; color: #991b1b; }}
    .pill-discrepancy {{ background: #ffedd5; color: #9a3412; }}
    .transcript h2 {{ margin-top: 0; }}
    .chat-item {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; background: #fff; }}
    .chat-item.user {{ border-color: #10b981; background: #f0fdf4; }}
    .chat-role {{ font-size: 0.75rem; color: #64748b; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .reply {{ font-size: 0.95rem; }}
    .reply h1 {{ font-size: 1.35rem; }}
    .reply h2 {{ font-size: 1.15rem; }}
    .reply h3 {{ font-size: 1.05rem; }}
    .reply p {{ margin: 6px 0 10px; }}
    .reply ul, .reply ol {{ margin: 6px 0 10px 22px; }}
    .reply table {{ width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 0.88rem; }}
    .reply th, .reply td {{ border: 1px solid #e2e8f0; padding: 8px 10px; }}
    .reply th {{ background: #f1f5f9; }}
    .footnote {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 0.8rem; color: #94a3b8; }}
    .annotated-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .annotated-card {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px; background: #fff; }}
    .annotated-head {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px; align-items: baseline; }}
    .annotated-preview {{ width: 100%; height: auto; display: block; border-radius: 8px; border: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="report-header">
      <h1>{escape(REPORT_BRAND_HEADER)}</h1>
      <p class="report-subhead">{escape(report_title)}</p>
      <div class="meta">
        <span><strong>Report ID</strong> {escape(report_id)}</span>
        <span><strong>Project</strong> {escape(project_name)}</span>
        <span><strong>Author</strong> {escape(author)}</span>
        <span><strong>Generated</strong> {escape(generated_at)}</span>
      </div>
    </header>
    {chart_html}
    {sections_html}
    {ann_html}
    {attached_ann_html}
    <section class="block transcript">
      <h2 class="section-title">Transcript &amp; narrative</h2>
      {''.join(chat_blocks_html) if chat_blocks_html else '<p class="muted">No transcript included.</p>'}
    </section>
    <p class="footnote">CIA Construction Insight Agent — exported document. Tables and charts are illustrative where sample data is used.</p>
  </div>
</body>
</html>
"""
    html_path.write_text(report_html, encoding="utf-8")

    annotated_assets = payload.get("annotated_drawing_assets") or []
    annotated_downloads: dict[str, str] = {}
    for i, asset in enumerate(annotated_assets, start=1):
        data_url = str(asset.get("image_data_url", "")).strip()
        image_bytes = _decode_png_data_url(data_url)
        if not image_bytes:
            continue
        stem = Path(str(asset.get("filename", f"drawing-{i}"))).stem
        clean_stem = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in stem).strip("-") or f"drawing-{i}"
        ann_name = f"{report_id}-annotated-{i}-{clean_stem}.png"
        ann_path = REPORTS_DIR / ann_name
        ann_path.write_bytes(image_bytes)
        annotated_downloads[f"annotated_png_{i}"] = f"/api/ai/reports/download/{ann_name}"

    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["type", "key", "value"])
        writer.writerow(["meta", "report_id", report_id])
        writer.writerow(["meta", "report_title", report_title])
        writer.writerow(["meta", "author", author])
        writer.writerow(["meta", "generated_at", generated_at])
        writer.writerow(["meta", "project_id", payload.get("project_id")])
        writer.writerow(["meta", "project_name", project_name])
        writer.writerow(["meta", "annotated_drawing_count", len(annotated_assets)])
        for key, value in section_rows:
            writer.writerow(["section", key, value])
        for i, asset in enumerate(annotated_assets, start=1):
            writer.writerow(
                [
                    "annotated_drawing",
                    str(i),
                    json.dumps(
                        {
                            "filename": str(asset.get("filename", "")),
                            "marker_count": len(asset.get("markers") or []),
                            "download_key": f"annotated_png_{i}",
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
        writer.writerow(["chat", "full_chat_text", full_chat_text])
        writer.writerow(["chat", "rendered_html_file", html_path.name])

    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Cover"
    ws.append(["Report title", report_title])
    ws.append(["Author", author])
    ws.append(["Generated", generated_at])
    ws.append(["Project", project_name])
    ws.append(["Report ID", report_id])
    ws["A1"].font = Font(bold=True)
    ws2 = wb.create_sheet("Summary")
    ws2.append(["Section", "Summary"])
    for key, value in section_rows:
        ws2.append([key, value])
    ws2.column_dimensions["A"].width = 32
    ws2.column_dimensions["B"].width = 110
    ws3 = wb.create_sheet("Annotations")
    ws3.append(["Drawing sheet", "Type", "Description", "Severity"])
    for row in payload.get("deficiency_annotation_samples") or []:
        ws3.append(
            [
                str(row.get("drawing_sheet", "")),
                str(row.get("annotation_type", "")),
                str(row.get("description", "")),
                str(row.get("severity", "")),
            ]
        )
    ws4 = wb.create_sheet("Transcript")
    ws4.append(["Role", "Timestamp", "Message (Markdown/Text)", "Message (HTML)"])
    for row in chat_rows:
        role = str(row.get("role", "assistant"))
        text = str(row.get("text", ""))
        html_text = (
            md.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
            if role == "assistant"
            else f"<p>{escape(text).replace(chr(10), '<br/>')}</p>"
        )
        ws4.append([role, str(row.get("created_at", "")), text, html_text])
    ws5 = wb.create_sheet("Attached Drawings")
    ws5.append(["Filename", "Markers", "Download key"])
    for i, asset in enumerate(annotated_assets, start=1):
        ws5.append(
            [
                str(asset.get("filename", "")),
                len(asset.get("markers") or []),
                f"annotated_png_{i}",
            ]
        )
    wb.save(xlsx_path)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="CIATitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=14,
        textColor=colors.HexColor("#0f172a"),
    )
    meta_style = ParagraphStyle(
        name="CIAMeta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        name="CIABody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )
    h2_style = ParagraphStyle(
        name="CIAH2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor("#0f172a"),
    )
    section_cell_style = ParagraphStyle(
        name="CIASectionCell",
        parent=body_style,
        fontSize=8,
        leading=10,
        spaceAfter=0,
        wordWrap="LTR",
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=52,
        bottomMargin=52,
    )
    story: list = []
    story.append(Paragraph(escape(REPORT_BRAND_HEADER), title_style))
    story.append(Paragraph(escape(report_title), h2_style))
    story.append(
        Paragraph(
            f"<b>Report ID:</b> {escape(report_id)} &nbsp;|&nbsp; "
            f"<b>Project:</b> {escape(project_name)} &nbsp;|&nbsp; "
            f"<b>Author:</b> {escape(author)} &nbsp;|&nbsp; "
            f"<b>Generated:</b> {escape(generated_at)}",
            meta_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Dashboard metrics (bar values)</b>", h2_style))
    chart = payload.get("chart_metrics") or {}
    bar_rows = [[escape(str(b.get("label", ""))), str(int(b.get("value", 0) or 0))] for b in chart.get("bars") or []]
    if bar_rows:
        t = Table([["Metric", "Value"]] + bar_rows, colWidths=[320, 80])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d1fae5")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Structured sections</b>", h2_style))
    if section_rows:
        # Plain strings in ReportLab Table cells are parsed as mini-markup; `<` / `&` in JSON
        # can blank a cell. Use Paragraph + XML-escaped text so full content always renders.
        sec_hdr = [
            Paragraph("<b>Section</b>", section_cell_style),
            Paragraph("<b>Summary / detail</b>", section_cell_style),
        ]
        sec_body = [
            [
                Paragraph(_pdf_table_cell_markup(key), section_cell_style),
                Paragraph(_pdf_table_cell_markup(val), section_cell_style),
            ]
            for key, val in section_rows
        ]
        sec_table = Table([sec_hdr] + sec_body, colWidths=[72, 330])
        sec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d1fae5")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(sec_table)
    else:
        story.append(Paragraph("No structured sections included.", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Deficiency &amp; discrepancy log</b>", h2_style))
    ann = payload.get("deficiency_annotation_samples") or []
    if ann:
        ann_data = [["Sheet", "Type", "Description", "Severity"]]
        for row in ann:
            ann_data.append(
                [
                    escape(str(row.get("drawing_sheet", ""))),
                    escape(str(row.get("annotation_type", ""))),
                    escape(str(row.get("description", "")))[:800],
                    escape(str(row.get("severity", ""))),
                ]
            )
        at = Table(ann_data, colWidths=[70, 80, 300, 55])
        at.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(at)
    else:
        story.append(Paragraph("No annotation samples in this export.", body_style))
    story.append(Spacer(1, 14))
    story.append(Paragraph("<b>Transcript</b>", h2_style))
    for row in chat_rows:
        role = str(row.get("role", "assistant"))
        created = str(row.get("created_at", ""))
        text = str(row.get("text", ""))
        label = "AI Assistant" if role == "assistant" else "You"
        story.append(Paragraph(f"<b>{escape(label)}</b> · {escape(created)}", body_style))
        safe = escape(text).replace("\n", "<br/>")
        story.append(Paragraph(safe, body_style))
        story.append(Spacer(1, 6))
    doc.build(story)

    from docx import Document
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from docx.shared import Pt

    docx_doc = Document()
    t_para = docx_doc.add_paragraph()
    t_run = t_para.add_run(REPORT_BRAND_HEADER)
    t_run.bold = True
    t_run.font.size = Pt(22)
    t_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    sub_para = docx_doc.add_paragraph()
    sub_run = sub_para.add_run(report_title)
    sub_run.bold = True
    sub_run.font.size = Pt(14)

    meta = docx_doc.add_paragraph()
    meta.add_run("Report ID: ").bold = True
    meta.add_run(f"{report_id}\n")
    meta.add_run("Project: ").bold = True
    meta.add_run(f"{project_name}\n")
    meta.add_run("Author: ").bold = True
    meta.add_run(f"{author}\n")
    meta.add_run("Generated: ").bold = True
    meta.add_run(generated_at)

    docx_doc.add_heading("Dashboard metrics", level=2)
    table = docx_doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Metric"
    hdr[1].text = "Value"
    for b in (payload.get("chart_metrics") or {}).get("bars") or []:
        row = table.add_row().cells
        row[0].text = str(b.get("label", ""))
        row[1].text = str(int(b.get("value", 0) or 0))

    docx_doc.add_heading("Structured sections", level=2)
    sec_table = docx_doc.add_table(rows=1, cols=2)
    sec_table.style = "Table Grid"
    sec_hdr = sec_table.rows[0].cells
    sec_hdr[0].text = "Section"
    sec_hdr[1].text = "Summary"
    for key, value in section_rows:
        row = sec_table.add_row().cells
        row[0].text = key
        val_str = str(value)
        if len(val_str) > 45000:
            val_str = val_str[:45000] + "\n\n[Truncated for Word cell size. Use HTML or JSON export for the full text.]"
        row[1].text = val_str

    docx_doc.add_heading("Deficiency & discrepancy annotations", level=2)
    docx_doc.add_paragraph(
        payload.get("annotated_preview_note")
        or "Record deficiencies (code / safety) and discrepancies (drawing vs schedule) with sheet references."
    )
    for row in payload.get("deficiency_annotation_samples") or []:
        p = docx_doc.add_paragraph(style="List Bullet")
        p.add_run(f"{row.get('annotation_type', '')} — {row.get('drawing_sheet', '')}: ").bold = True
        p.add_run(str(row.get("description", "")))

    docx_doc.add_heading("Attached annotated drawings", level=2)
    if annotated_assets:
        for i, asset in enumerate(annotated_assets, start=1):
            p = docx_doc.add_paragraph(style="List Bullet")
            p.add_run(f"{asset.get('filename', f'Drawing {i}')} ").bold = True
            p.add_run(f"({len(asset.get('markers') or [])} marker(s), download key: annotated_png_{i})")
    else:
        docx_doc.add_paragraph("No annotated drawings attached.")

    docx_doc.add_heading("Transcript", level=2)
    for row in chat_rows:
        p = docx_doc.add_paragraph()
        p.add_run(f"[{str(row.get('role', 'assistant')).upper()}] ").bold = True
        p.add_run(str(row.get("created_at", "")))
        docx_doc.add_paragraph(str(row.get("text", "")))
    docx_doc.save(docx_path)

    return {
        "json": f"/api/ai/reports/download/{json_path.name}",
        "csv": f"/api/ai/reports/download/{csv_path.name}",
        "excel": f"/api/ai/reports/download/{xlsx_path.name}",
        "pdf": f"/api/ai/reports/download/{pdf_path.name}",
        "word": f"/api/ai/reports/download/{docx_path.name}",
        "html": f"/api/ai/reports/download/{html_path.name}",
        **annotated_downloads,
    }


@router.post("/reports/standard")
def generate_standard_report(
    body: ConsolidatedReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == body.project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    report_id = f"standard-{body.project_id}-{uuid4().hex[:8]}"
    derived_prompts: list[str] = []
    for row in body.chat_history:
        if str(row.get("role", "")).lower() != "user":
            continue
        text = str(row.get("text", "")).strip()
        if text:
            derived_prompts.append(text)
    payload = _report_payload(
        body.project_id,
        prompts=derived_prompts,
        chat_history=body.chat_history,
        annotation_assets=body.annotation_assets,
    )
    _apply_report_metadata(payload, project, "Standard AI Assistant Report", body.author)
    files = _write_report_files(report_id, payload)
    return {"report_type": "standard", "report_id": report_id, "payload": payload, "downloads": files}


@router.post("/reports/consolidated")
def generate_consolidated_report(
    body: ConsolidatedReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == body.project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    report_id = f"consolidated-{body.project_id}-{uuid4().hex[:8]}"
    payload = _report_payload(
        body.project_id,
        body.user_prompts,
        body.chat_history,
        body.annotation_assets,
    )
    _apply_report_metadata(payload, project, "Consolidated AI Assistant Report", body.author)
    files = _write_report_files(report_id, payload)
    return {"report_type": "consolidated", "report_id": report_id, "payload": payload, "downloads": files}


@router.post("/reports/consolidate-collection")
def generate_consolidate_collection_report(
    body: ConsolidateCollectionReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == body.project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    report_id = f"consolidated-collection-{body.project_id}-{uuid4().hex[:8]}"
    transcript: list[dict] = []
    for item in body.items:
        header = f"### {item.label}\n_Source: {item.source}_ · _ID: {item.id or '—'}_\n\n"
        transcript.append(
            {
                "role": "assistant",
                "text": header + item.text,
                "created_at": item.created_at or "",
            }
        )
    payload = _report_payload(
        body.project_id,
        chat_history=transcript,
        annotation_assets=[a.model_dump() for a in body.annotation_assets],
    )
    merged_sections = _merged_sections_from_collected_prompts(body.items, body.chat_history)
    collected_gs: dict[str, str] = {}
    for idx, item in enumerate(body.items, start=1):
        label = (item.label or f"Output {idx}").strip()
        if len(label) > 76:
            label = f"{label[:73]}..."
        collected_gs[f"Collected {idx}: {label}"] = (
            f"Source: {item.source}\nID: {item.id or '—'}\nCreated: {item.created_at or '—'}\n\n{item.text}"
        )
    payload["generated_sections"] = {**merged_sections, **collected_gs, **payload["generated_sections"]}
    payload["collected_materials"] = [m.model_dump() for m in body.items]
    _apply_report_metadata(payload, project, "Consolidated Report (Collected Outputs)", body.author)
    files = _write_report_files(report_id, payload)
    return {"report_type": "consolidated_collection", "report_id": report_id, "payload": payload, "downloads": files}


@router.get("/reports/download/{filename}")
def download_report_file(filename: str, _: User = Depends(get_current_user)):
    path = REPORTS_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)
