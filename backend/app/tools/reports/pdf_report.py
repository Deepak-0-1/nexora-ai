import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel, GENERATED_DIR
from backend.db import connect as connect_app_db

class GeneratePdfReportInput(BaseModel):
    title: str = Field(description="Title of the PDF report")
    summary: str = Field(description="Executive summary paragraph")
    sections: List[Dict[str, str]] = Field(description="List of sections: [{'heading': 'Findings', 'content': 'Text...'}]")
    filename: Optional[str] = Field(default=None, description="Output PDF filename (e.g. market_report.pdf)")

class GeneratePdfReportTool(BaseTool):
    name = "generate_pdf_report"
    description = "Generates a clean, professional PDF document (.pdf) with title, summary, and sections."
    input_schema = GeneratePdfReportInput
    permission_level = PermissionLevel.GENERATE

    async def execute(
        self,
        title: str,
        summary: str,
        sections: List[Dict[str, str]],
        filename: Optional[str] = None
    ) -> ToolResult:
        def _build_pdf():
            fname = filename or f"report_{uuid.uuid4().hex[:8]}.pdf"
            if not fname.endswith(".pdf"):
                fname += ".pdf"

            dest = Path(GENERATED_DIR) / fname
            doc = SimpleDocTemplate(str(dest), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor('#1F497D'),
                spaceAfter=14
            )
            heading_style = ParagraphStyle(
                'ReportHeading',
                parent=styles['Heading2'],
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#2E5B82'),
                spaceBefore=12,
                spaceAfter=6
            )
            body_style = styles['Normal']
            body_style.fontSize = 10
            body_style.leading = 14

            story = [
                Paragraph(title, title_style),
                Spacer(1, 10),
                Paragraph("<b>Executive Summary</b>", heading_style),
                Paragraph(summary, body_style),
                Spacer(1, 14)
            ]

            for sec in sections:
                h = sec.get("heading", "Section")
                c = sec.get("content", "")
                story.append(Paragraph(h, heading_style))
                story.append(Paragraph(c.replace("\n", "<br/>"), body_style))
                story.append(Spacer(1, 10))

            doc.build(story)

            # Record in generated_artifacts table
            with connect_app_db() as conn:
                conn.execute(
                    """
                    INSERT INTO generated_artifacts (id, filename, file_type, file_path, size_bytes)
                    VALUES (?, ?, 'pdf', ?, ?)
                    """,
                    (f"art_{uuid.uuid4().hex[:10]}", fname, str(dest), dest.stat().st_size)
                )

            return dest

        try:
            dest_path = await asyncio.to_thread(_build_pdf)
            return ToolResult(
                success=True,
                data={
                    "filename": dest_path.name,
                    "file_path": str(dest_path),
                    "size_bytes": dest_path.stat().st_size,
                    "message": f"PDF report successfully created: {dest_path.name}"
                },
                metadata={"file_path": str(dest_path), "filename": dest_path.name}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"PDF generation failed: {str(e)}")

