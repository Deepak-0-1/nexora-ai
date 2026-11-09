import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.tools.excel.processor import excel_processor
from backend.app.security.file_validator import is_safe_local_path

class ListExcelSheetsInput(BaseModel):
    file_path: str = Field(description="Path to the Excel file")

class ListExcelSheetsTool(BaseTool):
    name = "list_excel_sheets"
    description = "Lists all worksheet names present in an Excel workbook."
    input_schema = ListExcelSheetsInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, file_path: str) -> ToolResult:
        safe, err, resolved = is_safe_local_path(file_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        try:
            sheets = await asyncio.to_thread(excel_processor.list_sheets, resolved)
            return ToolResult(
                success=True,
                data={"file_path": str(resolved), "sheets": sheets, "count": len(sheets)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class PreviewDataframeInput(BaseModel):
    file_path: str = Field(description="Path to Excel (.xlsx) or CSV (.csv) file")
    sheet_name: Optional[str] = Field(default=None, description="Optional sheet name for Excel")
    max_rows: int = Field(default=10, ge=1, le=50, description="Number of preview rows to return")

class PreviewDataframeTool(BaseTool):
    name = "preview_data_file"
    description = "Reads an Excel or CSV file and returns the first N rows along with column headers."
    input_schema = PreviewDataframeInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, file_path: str, sheet_name: Optional[str] = None, max_rows: int = 10) -> ToolResult:
        safe, err, resolved = is_safe_local_path(file_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        try:
            def _load_and_preview():
                df = excel_processor.load_dataframe(resolved, sheet_name=sheet_name)
                head = df.head(max_rows)
                # replace NaN with None for valid JSON serialization
                records = head.where(head.notnull(), None).to_dict(orient="records")
                return {
                    "columns": [str(c) for c in df.columns],
                    "total_rows": len(df),
                    "preview_rows": records
                }

            res = await asyncio.to_thread(_load_and_preview)
            return ToolResult(success=True, data=res)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ProfileDataframeInput(BaseModel):
    file_path: str = Field(description="Path to Excel or CSV file to profile")
    sheet_name: Optional[str] = Field(default=None, description="Optional sheet name")

class ProfileDataframeTool(BaseTool):
    name = "profile_data_file"
    description = "Performs data profiling: columns, null percentages, data types, uniques, and statistical summaries."
    input_schema = ProfileDataframeInput
    permission_level = PermissionLevel.ANALYSIS

    async def execute(self, file_path: str, sheet_name: Optional[str] = None) -> ToolResult:
        safe, err, resolved = is_safe_local_path(file_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        try:
            def _profile():
                df = excel_processor.load_dataframe(resolved, sheet_name=sheet_name)
                return excel_processor.profile_dataframe(df)

            profile = await asyncio.to_thread(_profile)
            return ToolResult(success=True, data=profile)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateExcelReportInput(BaseModel):
    title: str = Field(description="Title of the executive report")
    summary_data: List[Dict[str, Any]] = Field(description="Rows of aggregated summary / KPI data")
    detailed_data: List[Dict[str, Any]] = Field(description="Rows of detailed processed records")
    filename: Optional[str] = Field(default=None, description="Output filename (e.g. quarterly_analysis.xlsx)")

class CreateExcelReportTool(BaseTool):
    name = "create_excel_report"
    description = "Generates a multi-sheet formatted Excel workbook (.xlsx) containing an Executive Summary and Detailed Data."
    input_schema = CreateExcelReportInput
    permission_level = PermissionLevel.GENERATE

    async def execute(
        self,
        title: str,
        summary_data: List[Dict[str, Any]],
        detailed_data: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> ToolResult:
        try:
            dest = await asyncio.to_thread(
                excel_processor.create_excel_report,
                title=title,
                summary_data=summary_data,
                detailed_data=detailed_data,
                output_filename=filename
            )
            return ToolResult(
                success=True,
                data={
                    "file_path": str(dest),
                    "filename": dest.name,
                    "size_bytes": dest.stat().st_size,
                    "message": f"Excel report generated successfully at {dest.name}"
                },
                metadata={"file_path": str(dest), "filename": dest.name}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

