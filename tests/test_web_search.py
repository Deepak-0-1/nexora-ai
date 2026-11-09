import pytest
from unittest.mock import patch, MagicMock
from backend.app.tools.web.search import WebSearchTool, OpenUrlTool
from backend.app.tools.web.extractor import extract_clean_text_from_html
from backend.app.security.path_validator import is_safe_url

def test_extract_clean_text_from_html():
    sample_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <script>var x = 123;</script>
            <style>body { color: red; }</style>
            <h1>Main Title</h1>
            <p>This is a paragraph with <b>bold</b> text and <a href="https://example.com">a link</a>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
    </html>
    """
    text = extract_clean_text_from_html(sample_html)
    assert "Main Title" in text
    assert "This is a paragraph with bold text and a link" in text
    assert "Item 1" in text
    assert "var x = 123;" not in text
    assert "color: red" not in text

def test_ssrf_protection():
    # Dangerous URLs
    assert is_safe_url("http://127.0.0.1/admin")[0] is False
    assert is_safe_url("http://localhost:8000/api")[0] is False
    assert is_safe_url("http://192.168.1.1/router")[0] is False
    assert is_safe_url("http://10.0.0.1/internal")[0] is False
    assert is_safe_url("ftp://example.com/file")[0] is False
    assert is_safe_url("file:///etc/passwd")[0] is False

    # Safe public URLs
    assert is_safe_url("https://example.com")[0] is True
    assert is_safe_url("https://en.wikipedia.org/wiki/Python_(programming_language)")[0] is True

@pytest.mark.anyio
async def test_web_search_tool_mocked():
    tool = WebSearchTool()
    mock_results = [
        {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
        {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"}
    ]

    with patch("backend.app.integrations.search_provider.default_search_provider.search", return_value=mock_results):
        res = await tool.execute(query="test query", max_results=2)
        assert res.success is True
        assert res.data["count"] == 2
        assert res.metadata["citations"] == ["https://example.com/1", "https://example.com/2"]

@pytest.mark.anyio
async def test_open_url_ssrf_blocked():
    tool = OpenUrlTool()
    res = await tool.execute(url="http://127.0.0.1:8000/secret")
    assert res.success is False
    assert "Security violation" in res.error

@pytest.mark.anyio
async def test_open_url_mocked_fetch():
    tool = OpenUrlTool()
    mock_resp = MagicMock()
    mock_resp.encoding = "utf-8"
    mock_resp.iter_content = MagicMock(return_value=[b"<html><body><h1>Docs</h1><p>Welcome to V3.</p></body></html>"])
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        res = await tool.execute(url="https://docs.example.com/guide")
        assert res.success is True
        assert "Docs" in res.data["content"]
        assert "Welcome to V3." in res.data["content"]
