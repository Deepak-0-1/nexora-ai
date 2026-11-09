import pytest
import pandas as pd
from pathlib import Path
from backend.app.tools.excel.tools import (
    ListExcelSheetsTool,
    PreviewDataframeTool,
    ProfileDataframeTool,
    CreateExcelReportTool
)
from backend.app.security.file_validator import is_safe_local_path

def test_file_validator_path_traversal(tmp_path):
    # Safe path in tmp_path
    sample_file = tmp_path / "test.csv"
    sample_file.write_text("a,b\n1,2")
    safe, _, _ = is_safe_local_path(str(sample_file), must_exist=True)
    assert safe is True

    # Non-existent file
    safe_no_exist, err_no_exist, _ = is_safe_local_path(str(tmp_path / "does_not_exist.csv"), must_exist=True)
    assert safe_no_exist is False
    assert "File not found" in err_no_exist

@pytest.mark.anyio
async def test_excel_and_csv_tools(tmp_path):
    # 1. Prepare sample CSV
    csv_file = tmp_path / "sales_data.csv"
    df = pd.DataFrame({
        "region": ["North", "South", "East", "West", "North"],
        "sales": [100.0, 250.5, None, 400.0, 100.0],
        "quantity": [2, 5, 1, 8, 2]
    })
    df.to_csv(csv_file, index=False)

    # 2. Preview data tool
    preview_tool = PreviewDataframeTool()
    res_prev = await preview_tool.execute(file_path=str(csv_file), max_rows=3)
    assert res_prev.success is True
    assert res_prev.data["total_rows"] == 5
    assert len(res_prev.data["preview_rows"]) == 3
    assert res_prev.data["columns"] == ["region", "sales", "quantity"]

    # 3. Profile data tool
    profile_tool = ProfileDataframeTool()
    res_prof = await profile_tool.execute(file_path=str(csv_file))
    assert res_prof.success is True
    prof = res_prof.data
    assert prof["total_rows"] == 5
    assert prof["total_columns"] == 3
    assert prof["duplicate_rows"] == 1  # 5th row is duplicate of 1st

    sales_col = next(c for c in prof["columns"] if c["name"] == "sales")
    assert sales_col["null_count"] == 1
    assert sales_col["null_percentage"] == 20.0

    # 4. Generate multi-sheet Excel report tool
    report_tool = CreateExcelReportTool()
    summary = [
        {"metric": "Total Revenue", "value": 850.5},
        {"metric": "Total Units", "value": 18}
    ]
    detailed = [
        {"region": "North", "sales": 200.0, "status": "Completed"},
        {"region": "South", "sales": 250.5, "status": "Completed"},
        {"region": "West", "sales": 400.0, "status": "Completed"}
    ]
    res_rep = await report_tool.execute(
        title="Quarterly Regional Sales Performance",
        summary_data=summary,
        detailed_data=detailed,
        filename="test_quarterly_report.xlsx"
    )
    assert res_rep.success is True
    out_path = Path(res_rep.data["file_path"])
    assert out_path.exists()
    assert out_path.name == "test_quarterly_report.xlsx"
    assert out_path.stat().st_size > 0

    # 5. List sheets of generated workbook
    sheets_tool = ListExcelSheetsTool()
    res_sheets = await sheets_tool.execute(file_path=str(out_path))
    assert res_sheets.success is True
    assert "Executive Summary" in res_sheets.data["sheets"]
    assert "Detailed Data" in res_sheets.data["sheets"]

