import asyncio
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.integrations.search_provider import default_search_provider
from backend.app.security.path_validator import is_safe_url
from backend.app.tools.web.extractor import extract_clean_text_from_html


class WebSearchInput(BaseModel):
    query: str = Field(description="Search terms or question to look up on the web")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of search results to retrieve")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Searches the web for up-to-date information, documentation, news, or articles."
    input_schema = WebSearchInput
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 20

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            results = await asyncio.to_thread(
                default_search_provider.search,
                query=query,
                max_results=max_results,
            )
            if not results:
                return ToolResult(
                    success=False,
                    error=(
                        f"Web search returned no usable results for: {query}. "
                        "No current information was verified. Do not answer this as a current-fact request "
                        "from model memory; report that the search could not be completed."
                    ),
                    metadata={"query": query, "result_count": 0},
                )

            return ToolResult(
                success=True,
                data={"query": query, "results": results, "count": len(results)},
                metadata={"citations": [result["url"] for result in results]},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Web search failed: {str(exc)}",
                metadata={"query": query},
            )


class OpenUrlInput(BaseModel):
    url: str = Field(description="The full HTTP/HTTPS URL of the webpage to open and read")
    max_chars: int = Field(default=8000, ge=500, le=30000, description="Max characters to extract from the webpage")


class OpenUrlTool(BaseTool):
    name = "open_url"
    description = "Opens a verified public URL, retrieves its HTML content, and extracts clean readable text."
    input_schema = OpenUrlInput
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 25

    async def execute(self, url: str, max_chars: int = 8000) -> ToolResult:
        safe, reason = is_safe_url(url)
        if not safe:
            return ToolResult(
                success=False,
                error=f"Security violation: {reason}",
            )

        def _fetch():
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()

            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=16384, decode_unicode=False):
                total += len(chunk)
                chunks.append(chunk)
                if total > 5 * 1024 * 1024:
                    break

            raw_bytes = b"".join(chunks)
            encoding = resp.encoding or "utf-8"
            try:
                html_text = raw_bytes.decode(encoding, errors="replace")
            except (LookupError, UnicodeError):
                html_text = raw_bytes.decode("utf-8", errors="replace")
            return extract_clean_text_from_html(html_text, max_chars=max_chars)

        try:
            extracted_text = await asyncio.to_thread(_fetch)
            if not extracted_text.strip():
                return ToolResult(
                    success=False,
                    error=f"No readable page content could be extracted from {url}.",
                    metadata={"url": url},
                )
            return ToolResult(
                success=True,
                data={"url": url, "content": extracted_text, "length": len(extracted_text)},
                metadata={"url": url},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to retrieve URL '{url}': {str(exc)}",
            )
