import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import init_db
from backend.app.agents.state import AgentPlan, AgentStep

client = TestClient(app)

def test_api_tools_endpoint():
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    names = [t["name"] for t in tools]
    assert "web_search" in names
    assert "execute_sql_query" in names
    assert "create_excel_report" in names
    assert "generate_docx_report" in names
    assert "generate_pdf_report" in names
    assert "execute_python" in names

def test_api_agent_lifecycle():
    init_db()

    mock_plan = AgentPlan(
        goal="Calculate quarterly revenue",
        steps=[]
    )

    with patch("backend.app.agents.planner.Planner.plan", return_value=mock_plan):
        # 1. Create run
        create_resp = client.post("/api/agent/runs", json={"query": "Calculate quarterly revenue", "conversation_id": "test_conv"})
        assert create_resp.status_code == 200
        data = create_resp.json()
        run_id = data["run_id"]
        assert "run_" in run_id

        # 2. Inspect run
        get_resp = client.get(f"/api/agent/runs/{run_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["run_id"] == run_id

        # 3. Stream run events
        stream_resp = client.get(f"/api/agent/runs/{run_id}/stream")
        assert stream_resp.status_code == 200
        assert "data: " in stream_resp.text

        # 4. Cancel run
        cancel_resp = client.post(f"/api/agent/runs/{run_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

def test_api_artifacts_endpoint():
    init_db()
    resp = client.get("/api/artifacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
