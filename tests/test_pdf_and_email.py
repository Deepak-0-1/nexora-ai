import pytest
from pathlib import Path
from backend.db import init_db, connect
from backend.app.tools.reports.pdf_report import GeneratePdfReportTool
from backend.app.tools.reports.email_tools import DraftEmailTool, SendEmailTool

@pytest.mark.anyio
async def test_generate_pdf_report():
    init_db()
    tool = GeneratePdfReportTool()

    title = "Executive Market Analysis Q4"
    summary = "Overview of modern local AI systems and local RAG capabilities."
    sections = [
        {"heading": "Key Highlights", "content": "1. Multi-step plan execution.\n2. In-memory approval checkpoints."},
        {"heading": "Next Actions", "content": "Deploy database connectors with row limits."}
    ]

    res = await tool.execute(
        title=title,
        summary=summary,
        sections=sections,
        filename="test_market_report.pdf"
    )

    assert res.success is True
    out_file = Path(res.data["file_path"])
    assert out_file.exists()
    assert out_file.name == "test_market_report.pdf"
    assert out_file.stat().st_size > 0

    with connect() as c:
        row = c.execute("SELECT * FROM generated_artifacts WHERE filename = ?", ("test_market_report.pdf",)).fetchone()
        assert row is not None
        assert row["file_type"] == "pdf"

@pytest.mark.anyio
async def test_email_tools():
    # 1. Draft email (read/generate level)
    draft_tool = DraftEmailTool()
    res_draft = await draft_tool.execute(
        recipient="manager@company.com",
        subject="Monthly Performance Report",
        body="Attached is the quarterly executive overview."
    )
    assert res_draft.success is True
    assert res_draft.data["status"] == "drafted"
    assert res_draft.data["recipient"] == "manager@company.com"

    # 2. Send email (external write level, requires approval)
    send_tool = SendEmailTool()
    assert send_tool.requires_approval is True
    res_send = await send_tool.execute(
        recipient="manager@company.com",
        subject="Monthly Performance Report",
        body="Attached is the quarterly executive overview."
    )
    assert res_send.success is True
    assert "queued_sent_simulation" in res_send.data["status"] or res_send.data["status"] == "sent"

