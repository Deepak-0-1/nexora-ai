from backend.app.tools.base import BaseTool, ToolResult
from backend.app.tools.registry import registry, ToolRegistry
from backend.app.tools.web import WebSearchTool, OpenUrlTool
from backend.app.tools.sql import (
    ListConnectionsTool,
    ListTablesTool,
    DescribeTableTool,
    ExecuteSqlTool
)
from backend.app.tools.excel import (
    ListExcelSheetsTool,
    PreviewDataframeTool,
    ProfileDataframeTool,
    CreateExcelReportTool
)

from backend.app.tools.documents import IndexDocumentTool, SearchDocumentsTool
from backend.app.tools.python import ExecutePythonTool
from backend.app.tools.files import ListFilesTool, ReadFileTool, CopyFileTool
from backend.app.tools.reports import (
    GenerateDocxReportTool,
    GeneratePdfReportTool,
    DraftEmailTool,
    SendEmailTool
)
from backend.app.tools.automations import (
    CreateReminderTool,
    CreateScheduleTool,
    ListSchedulesTool
)

# Register default built-in tools
registry.register(WebSearchTool())
registry.register(OpenUrlTool())
registry.register(ListConnectionsTool())
registry.register(ListTablesTool())
registry.register(DescribeTableTool())
registry.register(ExecuteSqlTool())
registry.register(ListExcelSheetsTool())
registry.register(PreviewDataframeTool())
registry.register(ProfileDataframeTool())
registry.register(CreateExcelReportTool())
registry.register(IndexDocumentTool())
registry.register(SearchDocumentsTool())
registry.register(ExecutePythonTool())
registry.register(ListFilesTool())
registry.register(ReadFileTool())
registry.register(CopyFileTool())
registry.register(GenerateDocxReportTool())
registry.register(GeneratePdfReportTool())
registry.register(DraftEmailTool())
registry.register(SendEmailTool())
registry.register(CreateReminderTool())
registry.register(CreateScheduleTool())
registry.register(ListSchedulesTool())

__all__ = [
    "BaseTool",
    "ToolResult",
    "registry",
    "ToolRegistry",
    "WebSearchTool",
    "OpenUrlTool",
    "ListConnectionsTool",
    "ListTablesTool",
    "DescribeTableTool",
    "ExecuteSqlTool",
    "ListExcelSheetsTool",
    "PreviewDataframeTool",
    "ProfileDataframeTool",
    "CreateExcelReportTool",
    "IndexDocumentTool",
    "SearchDocumentsTool",
    "ExecutePythonTool",
    "ListFilesTool",
    "ReadFileTool",
    "CopyFileTool",
    "GenerateDocxReportTool",
    "GeneratePdfReportTool",
    "DraftEmailTool",
    "SendEmailTool",
    "CreateReminderTool",
    "CreateScheduleTool",
    "ListSchedulesTool"
]

