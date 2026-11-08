import re
from typing import Tuple, List

FORBIDDEN_SQL_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bPRAGMA\b",
    r"\bVACUUM\b",
    r"\bCALL\b"
]

def sanitize_and_validate_sql(sql: str) -> Tuple[bool, str, str]:
    """
    Validates that a SQL statement is strictly READ-ONLY:
    - Removes comments (-- and /* */)
    - Rejects multiple semicolon-separated statements to prevent stacked injection
    - Ensures statement starts with SELECT or WITH (for CTEs) or EXPLAIN
    - Blocks any write, DDL, or administrative keywords
    Returns: (is_valid, sanitized_sql, error_reason)
    """
    if not sql or not sql.strip():
        return False, "", "Empty SQL query."

    # Remove single-line comments (-- ...)
    clean = re.sub(r"--[^\n]*", "", sql)
    # Remove block comments (/* ... */)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
    clean = clean.strip()

    if not clean:
        return False, "", "Query contains only comments or whitespace."

    # Check for multiple statements (semicolon inside query)
    statements = [s.strip() for s in clean.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "", "Multiple SQL statements in a single execution are prohibited."

    single_query = statements[0]

    # Ensure query begins with permitted read-only prefix
    first_token_match = re.match(r"^\s*([a-zA-Z]+)", single_query)
    if not first_token_match:
        return False, "", "Unable to identify SQL statement keyword."

    first_keyword = first_token_match.group(1).upper()
    if first_keyword not in ("SELECT", "WITH", "EXPLAIN"):
        return False, "", f"Operation '{first_keyword}' not allowed. Only SELECT and WITH (CTE) queries are permitted."

    # Check forbidden write/admin keywords using regex word boundary
    for pat in FORBIDDEN_SQL_KEYWORDS:
        match = re.search(pat, single_query, flags=re.IGNORECASE)
        if match:
            forbidden_kw = match.group(0).upper()
            return False, "", f"Security violation: Forbidden keyword '{forbidden_kw}' detected in query."

    return True, single_query, ""

