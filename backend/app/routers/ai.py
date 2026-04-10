import httpx
from pathlib import Path
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

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "storage" / "reports"


class ProjectAIChatRequest(AIChatRequest):
    project_id: int


class ConsolidatedReportRequest(BaseModel):
    project_id: int
    user_prompts: list[str] = Field(default_factory=list, max_length=20)


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


def _report_payload(project_id: int, prompts: list[str] | None = None) -> dict:
    base = {
        "project_id": project_id,
        "generated_sections": {
            "4.1": "Space detection, room labels, dimensions, symbols, materials",
            "4.2": "Gross Floor Area (GFA) vs Usable/Net Area calculation",
            "4.3": "Space-type summary table with efficiency ratio",
            "4.4": "Statistical dashboard with total GFA/usable area/pie chart-ready data",
            "4.5": {
                "manual_reinspection_required": [
                    {
                        "item": "North stair dimension extraction",
                        "doubt_score": 78,
                        "manual_review_reason": "Low OCR confidence on boundary text",
                    }
                ]
            },
            "4.6": "LLM-generated corrective action suggestions",
            "4.7": "LangGraph toolchain summary (retrieve/check/summary/area/doubt tools)",
            "compliance": {
                "status": "MVP parser output",
                "citations": [
                    {"section": "HK Code Sec. 12.4", "drawing_page": "A-103"}
                ],
            },
        },
        "citations": [{"source": "HK regulation sample", "confidence": 0.76, "doubt_score": 24}],
        "annotated_preview_note": "Issue overlays should be shown in red on drawing previews.",
    }
    if prompts:
        base["selected_user_prompts"] = prompts
    return base


def _write_report_files(report_id: str, payload: dict) -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / f"{report_id}.json"
    csv_path = REPORTS_DIR / f"{report_id}.csv"
    xlsx_path = REPORTS_DIR / f"{report_id}.xlsx"
    pdf_path = REPORTS_DIR / f"{report_id}.pdf"
    docx_path = REPORTS_DIR / f"{report_id}.docx"
    json_text = __import__("json").dumps(payload, indent=2)
    json_path.write_text(json_text, encoding="utf-8")
    csv_path.write_text("section,summary\n4.1,Space extraction\n4.2,Area calc\n", encoding="utf-8")

    # Generate a valid XLSX workbook
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Section", "Summary"])
    ws.append(["4.1", "Space detection, room labels, dimensions, symbols, materials"])
    ws.append(["4.2", "Gross Floor Area vs Usable/Net Area calculation"])
    ws.append(["4.3", "Space-type summary table with efficiency ratio"])
    ws.append(["4.4", "Statistical dashboard metrics"])
    ws.append(["4.5", "Missing data and doubt flags"])
    ws.append(["4.6", "Corrective action suggestions"])
    ws.append(["4.7", "Conversational agent toolchain"])
    wb.save(xlsx_path)

    # Generate a valid PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "AI Assistant Report")
    c.setFont("Helvetica", 10)
    y = 780
    for line in [
        f"Report ID: {report_id}",
        f"Project ID: {payload.get('project_id')}",
        "Sections: 4.1 to 4.7 included",
        "Contains citations, confidence, and doubt flags.",
    ]:
        c.drawString(50, y, line)
        y -= 16
    c.showPage()
    c.save()

    # Generate a valid DOCX
    from docx import Document

    doc = Document()
    doc.add_heading("AI Assistant Report", level=1)
    doc.add_paragraph(f"Report ID: {report_id}")
    doc.add_paragraph(f"Project ID: {payload.get('project_id')}")
    doc.add_paragraph("Sections 4.1 to 4.7 are included.")
    doc.add_paragraph("Includes citations, confidence, and doubt flags.")
    doc.save(docx_path)

    return {
        "json": f"/api/ai/reports/download/{json_path.name}",
        "csv": f"/api/ai/reports/download/{csv_path.name}",
        "excel": f"/api/ai/reports/download/{xlsx_path.name}",
        "pdf": f"/api/ai/reports/download/{pdf_path.name}",
        "word": f"/api/ai/reports/download/{docx_path.name}",
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
    payload = _report_payload(body.project_id)
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
    payload = _report_payload(body.project_id, body.user_prompts)
    files = _write_report_files(report_id, payload)
    return {"report_type": "consolidated", "report_id": report_id, "payload": payload, "downloads": files}


@router.get("/reports/download/{filename}")
def download_report_file(filename: str, _: User = Depends(get_current_user)):
    path = REPORTS_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)
