import os
import sqlite3
import pytest
from backend.db import init_db
from backend.app.security.sql_validator import sanitize_and_validate_sql
from backend.app.integrations.database_connectors import db_manager
from backend.app.tools.sql.database import (
    ListConnectionsTool,
    ListTablesTool,
    DescribeTableTool,
    ExecuteSqlTool
)

def test_sql_validator_blocks_destructive_operations():
    # Write and DDL statements should be blocked
    assert sanitize_and_validate_sql("DELETE FROM users")[0] is False
    assert sanitize_and_validate_sql("DROP TABLE orders")[0] is False
    assert sanitize_and_validate_sql("UPDATE accounts SET balance=0")[0] is False
    assert sanitize_and_validate_sql("INSERT INTO logs VALUES(1, 'hack')")[0] is False
    assert sanitize_and_validate_sql("TRUNCATE TABLE customers")[0] is False
    assert sanitize_and_validate_sql("ALTER TABLE users ADD COLUMN is_admin INT")[0] is False
    assert sanitize_and_validate_sql("PRAGMA foreign_keys = OFF")[0] is False

    # Multiple statements / stacked queries blocked
    assert sanitize_and_validate_sql("SELECT 1; DROP TABLE users;")[0] is False

    # Valid read-only queries should pass
    valid, clean, err = sanitize_and_validate_sql("SELECT id, name FROM users WHERE active = 1")
    assert valid is True
    assert clean == "SELECT id, name FROM users WHERE active = 1"

    # CTE should pass
    valid_cte, _, _ = sanitize_and_validate_sql("WITH ranked AS (SELECT id FROM sales) SELECT * FROM ranked")
    assert valid_cte is True

@pytest.mark.anyio
async def test_sql_tools_with_sqlite_db(tmp_path):
    init_db()

    # Create a dummy sample SQLite database
    sample_db_file = tmp_path / "sample_sales.db"
    with sqlite3.connect(sample_db_file) as conn:
        conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, balance REAL)")
        conn.execute("INSERT INTO customers (name, balance) VALUES ('Alice', 1500.0)")
        conn.execute("INSERT INTO customers (name, balance) VALUES ('Bob', 3200.5)")
        conn.commit()

    conn_id = "test_sales_db"
    db_manager.register_connection(
        conn_id=conn_id,
        name="Sales Database",
        dialect="sqlite",
        connection_uri=str(sample_db_file),
        read_only=True
    )

    # 1. Test ListConnectionsTool
    list_tool = ListConnectionsTool()
    res_conns = await list_tool.execute()
    assert res_conns.success is True
    assert any(c["id"] == conn_id for c in res_conns.data["connections"])

    # 2. Test ListTablesTool
    tables_tool = ListTablesTool()
    res_tables = await tables_tool.execute(connection_id=conn_id)
    assert res_tables.success is True
    assert any(t["table_name"] == "customers" for t in res_tables.data["tables"])

    # 3. Test DescribeTableTool
    desc_tool = DescribeTableTool()
    res_desc = await desc_tool.execute(connection_id=conn_id, table_name="customers")
    assert res_desc.success is True
    col_names = [col["name"] for col in res_desc.data["columns"]]
    assert "id" in col_names
    assert "name" in col_names
    assert "balance" in col_names

    # 4. Test ExecuteSqlTool (Valid SELECT)
    exec_tool = ExecuteSqlTool()
    res_exec = await exec_tool.execute(
        connection_id=conn_id,
        sql="SELECT name, balance FROM customers ORDER BY balance DESC",
        max_rows=10
    )
    assert res_exec.success is True
    assert res_exec.data["row_count"] == 2
    assert res_exec.data["rows"][0]["name"] == "Bob"
    assert res_exec.data["rows"][0]["balance"] == 3200.5

    # 5. Test ExecuteSqlTool (Security block write attempt)
    res_bad = await exec_tool.execute(
        connection_id=conn_id,
        sql="DELETE FROM customers WHERE id = 1"
    )
    assert res_bad.success is False
    assert "not allowed" in res_bad.error or "Security violation" in res_bad.error
