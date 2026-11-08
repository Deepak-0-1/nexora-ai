import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.integrations.database_connectors import db_manager
from backend.app.security.sql_validator import sanitize_and_validate_sql

class ListConnectionsInput(BaseModel):
    pass

class ListConnectionsTool(BaseTool):
    name = "list_database_connections"
    description = "Lists all configured database connections available to query."
    input_schema = ListConnectionsInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self) -> ToolResult:
        try:
            conns = await asyncio.to_thread(db_manager.list_connections)
            return ToolResult(
                success=True,
                data={"connections": conns, "count": len(conns)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ListTablesInput(BaseModel):
    connection_id: str = Field(description="The ID of the configured database connection")

class ListTablesTool(BaseTool):
    name = "list_database_tables"
    description = "Lists all tables and views available in a database connection."
    input_schema = ListTablesInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, connection_id: str) -> ToolResult:
        try:
            tables = await asyncio.to_thread(db_manager.list_tables, connection_id)
            return ToolResult(
                success=True,
                data={"connection_id": connection_id, "tables": tables, "count": len(tables)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class DescribeTableInput(BaseModel):
    connection_id: str = Field(description="The ID of the configured database connection")
    table_name: str = Field(description="Name of the table to inspect")

class DescribeTableTool(BaseTool):
    name = "describe_database_table"
    description = "Describes schema, columns, and data types of a specific table."
    input_schema = DescribeTableInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, connection_id: str, table_name: str) -> ToolResult:
        try:
            schema_info = await asyncio.to_thread(db_manager.describe_table, connection_id, table_name)
            return ToolResult(
                success=True,
                data={"connection_id": connection_id, "table_name": table_name, "columns": schema_info}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ExecuteSqlInput(BaseModel):
    connection_id: str = Field(description="The ID of the configured database connection")
    sql: str = Field(description="Strictly read-only SELECT query to execute")
    max_rows: int = Field(default=100, ge=1, le=500, description="Max rows to return")

class ExecuteSqlTool(BaseTool):
    name = "execute_sql_query"
    description = "Safely executes a read-only SELECT or CTE SQL query against a registered database and returns tabular results."
    input_schema = ExecuteSqlInput
    permission_level = PermissionLevel.ANALYSIS
    timeout_seconds = 30

    async def execute(self, connection_id: str, sql: str, max_rows: int = 100) -> ToolResult:
        valid, clean_sql, reason = sanitize_and_validate_sql(sql)
        if not valid:
            return ToolResult(
                success=False,
                error=f"SQL validation error: {reason}"
            )

        try:
            result = await asyncio.to_thread(
                db_manager.execute_read_query,
                connection_id=connection_id,
                query=clean_sql,
                max_rows=max_rows
            )
            return ToolResult(
                success=True,
                data=result,
                metadata={"connection_id": connection_id, "rows_returned": result["row_count"]}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"SQL execution failed: {str(e)}"
            )

