"""Capability-based routing for Nexora's built-in tools.

The router narrows the planner's candidate set; it does not execute tools.
Ambiguous or multi-domain requests retain multiple relevant capabilities.
"""
from dataclasses import dataclass
from typing import FrozenSet, List

@dataclass(frozen=True)
class Route:
    capabilities: FrozenSet[str]
    reason: str

TOOL_CAPABILITIES = {
    "web": {"web_search", "open_url"},
    "documents": {"index_document", "search_documents", "read_file"},
    "data": {"list_excel_sheets", "preview_data_file", "profile_data_file", "create_excel_report"},
    "sql": {"list_database_connections", "list_database_tables", "describe_database_table", "execute_sql_query"},
    "files": {"list_files", "read_file", "copy_file"},
    "python": {"execute_python"},
    "reports": {"generate_pdf_report", "generate_docx_report", "create_excel_report"},
    "email": {"draft_email", "send_email"},
    "automation": {"create_reminder", "create_schedule", "list_schedules"},
}

RULES = {
    "web": ("search the web", "web search", "internet", "latest", "current news", "online", "research", "website", "url", "documentation"),
    "documents": ("pdf", "document", "uploaded file", "indexed", "in the report", "in this file", "ask this file", "summarize this file"),
    "data": ("excel", "spreadsheet", "csv", "workbook", "dataframe", "dataset", "rows", "columns", "missing values", "statistics", "profile data"),
    "sql": ("database", "sql", "query", "table", "tables", "schema", "revenue", "records"),
    "files": ("list files", "read file", "copy file", "folder", "directory", "local file"),
    "python": ("calculate", "compute", "run python", "execute python", "plot", "chart", "statistical test"),
    "reports": ("generate a report", "create a report", "pdf report", "word report", "docx", "excel report"),
    "email": ("email", "e-mail", "send a message", "draft a message"),
    "automation": ("remind me", "reminder", "schedule", "every day", "every week", "recurring", "automatically"),
}

class ToolRouter:
    """Select relevant tool capabilities using conservative phrase matching."""

    def route(self, query: str) -> Route:
        text = " ".join((query or "").lower().split())
        matched = set()
        for capability, phrases in RULES.items():
            if any(phrase in text for phrase in phrases):
                matched.add(capability)

        # Explicitly preserve multi-stage data workflows.
        if any(x in text for x in ("database", "sql", "table", "query")):
            matched.add("sql")
        if any(x in text for x in ("excel", "spreadsheet", "csv")):
            matched.add("data")
        if not matched:
            return Route(frozenset(), "No tool capability confidently matched; treat as conversational.")
        return Route(frozenset(matched), "Matched request language to tool capabilities.")

    def candidate_tool_names(self, query: str) -> List[str]:
        route = self.route(query)
        names = set()
        for capability in route.capabilities:
            names.update(TOOL_CAPABILITIES[capability])
        return sorted(names)

tool_router = ToolRouter()
