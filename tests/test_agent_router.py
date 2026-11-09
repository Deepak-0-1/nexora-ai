from backend.app.agents.router import tool_router


def test_conversational_request_does_not_select_tools():
    assert tool_router.candidate_tool_names("Explain what a vector database is") == []


def test_web_search_request_selects_web_tools():
    names = tool_router.candidate_tool_names("Search the web for the latest LangGraph release")
    assert "web_search" in names
    assert "open_url" in names


def test_spreadsheet_request_selects_data_tools():
    names = tool_router.candidate_tool_names("Profile this CSV and find missing values")
    assert "profile_data_file" in names
    assert "preview_data_file" in names


def test_database_request_selects_sql_tools():
    names = tool_router.candidate_tool_names("List database connections and show tables")
    assert "list_database_connections" in names
    assert "list_database_tables" in names
    assert "execute_sql_query" in names


def test_document_search_selects_rag_tools():
    names = tool_router.candidate_tool_names("Search the indexed annual report")
    assert "search_documents" in names


def test_email_draft_does_not_expose_send_tool_without_email_capability():
    names = tool_router.candidate_tool_names("Draft an email to the recruiter")
    assert "draft_email" in names
    assert "send_email" in names
