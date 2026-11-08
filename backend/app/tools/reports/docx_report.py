import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel, GENERATED_DIR
from backend.db import connect as connect_app_db

class GenerateDocxReportInput(BaseModel):
    title: str = Field(description="Title of the Word report")
    sections: List[Dict[str, str]] = Field(description="List of sections: [{'heading': 'Overview', 'content': 'Text...'}]")
    key_findings: Optional[List[str]] = Field(default=None, description="Optional bullet points of key takeaways")
    filename: Optional[str] = Field(default=None, description="Output filename (e.g. market_research_report.docx)")

class GenerateDocxReportTool(BaseTool):
    name = "generate_docx_report"
    description = "Generates a professional formatted Microsoft Word document (.docx) with headings, bullet points, and typography."
    input_schema = GenerateDocxReportInput
    permission_level = PermissionLevel.GENERATE

    async def execute(
        self,
        title: str,
        sections: List[Dict[str, str]],
        key_findings: Optional[List[str]] = None,
        filename: Optional[str] = None
    ) -> ToolResult:
        def _build_doc():
            doc = docx.Document()

            # Set title
            t = doc.add_heading(title, level=0)
            t.paragraph_format.space_after = Pt(12)

            # Key findings bullet list
            if key_findings:
                doc.add_heading("Executive Takeaways", level=1)
                for item in key_findings:
                    doc.add_paragraph(item, style='List Bullet')

            # Sections
            for sec in sections:
                heading = sec.get("heading", "Section")
                content = sec.get("content", "")
                doc.add_heading(heading, level=1)
                for p_text in content.split("\n\n"):
                    if p_text.strip():
                        doc.add_paragraph(p_text.strip())

            fname = filename or f"report_{uuid.uuid4().hex[:8]}.docx"
            if not fname.endswith(".docx"):
                fname += ".docx"

            dest = Path(GENERATED_DIR) / fname
            doc.save(str(dest))

            # Register artifact in internal database
            with connect_app_db() as c:
                c.execute(
                    """
                    INSERT INTO generated_artifacts (id, filename, file_type, file_path, size_bytes)
                    VALUES (?, ?, 'docx', ?, ?)
                    """,
                    (f"art_{uuid.uuid4().hex[:10]}", fname, str(dest), dest.stat().st_size)
                )

            return dest

        try:
            dest_path = await asyncio.to_thread(_build_doc)
            return ToolResult(
                success=True,
                data={
                    "filename": dest_path.name,
                    "file_path": str(dest_path),
                    "size_bytes": dest_path.stat().st_size,
                    "message": f"Word report successfully generated: {dest_path.name}"
                },
                metadata={"file_path": str(dest_path), "filename": dest_path.name}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to generate Word report: {str(e)}")

