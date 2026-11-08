import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from backend.app.config import GENERATED_DIR

class ExcelProcessor:
    """Handles Excel and CSV loading, data profiling, summary calculation, and report creation."""

    def load_dataframe(self, file_path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
        ext = file_path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(file_path, sheet_name=sheet_name or 0)
        else:
            raise ValueError(f"Unsupported spreadsheet format: '{ext}'. Use .xlsx or .csv")

    def list_sheets(self, file_path: Path) -> List[str]:
        ext = file_path.suffix.lower()
        if ext in (".xlsx", ".xls"):
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheets = wb.sheetnames
            wb.close()
            return sheets
        elif ext == ".csv":
            return ["CSV_Data"]
        else:
            raise ValueError(f"Unsupported spreadsheet format: '{ext}'")

    def profile_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        total_rows = len(df)
        columns_info = []

        for col in df.columns:
            s = df[col]
            null_count = int(s.isnull().sum())
            unique_count = int(s.nunique())
            dtype_str = str(s.dtype)

            col_data = {
                "name": str(col),
                "type": dtype_str,
                "null_count": null_count,
                "null_percentage": round((null_count / total_rows * 100), 2) if total_rows > 0 else 0,
                "unique_values": unique_count,
            }

            if pd.api.types.is_numeric_dtype(s) and not s.dropna().empty:
                col_data["mean"] = round(float(s.mean()), 2)
                col_data["std"] = round(float(s.std()), 2) if not pd.isna(s.std()) else 0
                col_data["min"] = float(s.min())
                col_data["max"] = float(s.max())
                col_data["median"] = float(s.median())

            columns_info.append(col_data)

        # Duplicate row count
        duplicates = int(df.duplicated().sum())

        return {
            "total_rows": total_rows,
            "total_columns": len(df.columns),
            "duplicate_rows": duplicates,
            "columns": columns_info
        }

    def create_excel_report(
        self,
        title: str,
        summary_data: List[Dict[str, Any]],
        detailed_data: List[Dict[str, Any]],
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generates a professional multi-sheet Excel report:
        Sheet 1: Executive Summary
        Sheet 2: Detailed Data
        """
        wb = openpyxl.Workbook()

        # Styles
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="1F497D")
        border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # 1. Executive Summary Sheet
        ws_sum = wb.active
        ws_sum.title = "Executive Summary"
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum["A1"] = title
        ws_sum["A1"].font = title_font

        # Populate summary rows
        if summary_data:
            keys = list(summary_data[0].keys())
            # Header
            for col_idx, key in enumerate(keys, 1):
                cell = ws_sum.cell(row=3, column=col_idx, value=str(key).replace("_", " ").title())
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row_idx, item in enumerate(summary_data, 4):
                for col_idx, key in enumerate(keys, 1):
                    val = item.get(key)
                    c = ws_sum.cell(row=row_idx, column=col_idx, value=val)
                    c.border = border

        # 2. Detailed Data Sheet
        ws_det = wb.create_sheet(title="Detailed Data")
        ws_det.views.sheetView[0].showGridLines = True

        if detailed_data:
            keys = list(detailed_data[0].keys())
            for col_idx, key in enumerate(keys, 1):
                cell = ws_det.cell(row=1, column=col_idx, value=str(key))
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row_idx, item in enumerate(detailed_data, 2):
                for col_idx, key in enumerate(keys, 1):
                    val = item.get(key)
                    c = ws_det.cell(row=row_idx, column=col_idx, value=val)
                    c.border = border

        # Auto-adjust column widths
        for sheet in (ws_sum, ws_det):
            for col in sheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # Save artifact
        fname = output_filename or f"report_{uuid.uuid4().hex[:8]}.xlsx"
        if not fname.endswith(".xlsx"):
            fname += ".xlsx"
        dest_path = Path(GENERATED_DIR) / fname
        wb.save(dest_path)
        wb.close()
        return dest_path

excel_processor = ExcelProcessor()

