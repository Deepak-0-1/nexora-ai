import pytest
from pathlib import Path
from backend.db import init_db, connect
from backend.app.tools.reports.docx_report import GenerateDocxReportTool

@pytest.mark.anyio
async def test_generate_docx_report():
    init_db()
    tool = GenerateDocxReportTool()

    title = "Annual AI Engineering Evaluation Report"
    key_findings = [
        "Modular tool architecture reduces system coupling.",
        "Local LLM execution with strict permissions secures user databases."
    ]
    sections = [
        {"heading": "Executive Summary", "content": "This document outlines our transition from V2 to V3."},
        {"heading": "Recommendations", "content": "1. Run database queries in read-only mode.\n2. Keep agent approval gates active."}
    ]

    res = await tool.execute(
        title=title,
        sections=sections,
        key_findings=key_findings,
        filename="test_ai_eval_report.docx"
    )

    assert res.success is True
    out_file = Path(res.data["file_path"])
    assert out_file.exists()
    assert out_file.name == "test_ai_eval_report.docx"
    assert out_file.stat().st_size > 0

    # Verify registered in generated_artifacts table
    with connect() as c:
        row = c.execute("SELECT * FROM generated_artifacts WHERE filename = ?", ("test_ai_eval_report.docx",)).fetchone()
        assert row is not None
        assert row["file_type"] == "docx"

