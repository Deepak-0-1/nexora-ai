import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.tools.documents.processor import doc_processor
from backend.app.security.file_validator import is_safe_local_path

class IndexDocumentInput(BaseModel):
    file_path: str = Field(description="Local path to PDF, DOCX, TXT, or MD document")
    document_id: Optional[str] = Field(default=None, description="Optional custom identifier for the document")

class IndexDocumentTool(BaseTool):
    name = "index_document"
    description = "Parses, chunks, and indexes a local document (PDF, DOCX, TXT, Markdown) into vector retrieval storage."
    input_schema = IndexDocumentInput
    permission_level = PermissionLevel.ANALYSIS
    timeout_seconds = 60

    async def execute(self, file_path: str, document_id: Optional[str] = None) -> ToolResult:
        safe, err, resolved = is_safe_local_path(file_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        doc_id = document_id or resolved.stem.lower().replace(" ", "_")
        try:
            chunk_count = await asyncio.to_thread(doc_processor.index_document, doc_id, resolved)
            return ToolResult(
                success=True,
                data={
                    "document_id": doc_id,
                    "filename": resolved.name,
                    "chunks_indexed": chunk_count,
                    "message": f"Successfully indexed {resolved.name} into {chunk_count} searchable chunks."
                },
                metadata={"document_id": doc_id, "filename": resolved.name}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Indexing failed: {str(e)}")

class SearchDocumentsInput(BaseModel):
    query: str = Field(description="Search question or keywords to locate inside indexed documents")
    document_id: Optional[str] = Field(default=None, description="Optional document ID to restrict search to")
    top_k: int = Field(default=4, ge=1, le=10, description="Max relevant passages to return")

class SearchDocumentsTool(BaseTool):
    name = "search_documents"
    description = "Searches indexed documents for passages answering a question, with document names and page numbers."
    input_schema = SearchDocumentsInput
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 20

    async def execute(self, query: str, document_id: Optional[str] = None, top_k: int = 4) -> ToolResult:
        try:
            chunks = await asyncio.to_thread(doc_processor.search_chunks, query, document_id, top_k)
            citations = [
                f"{ch['filename']} (p. {ch['page_number']})"
                for ch in chunks
            ]
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": chunks,
                    "count": len(chunks)
                },
                metadata={"citations": citations}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Document search failed: {str(e)}")

