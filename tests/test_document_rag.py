import pytest
from unittest.mock import patch
from pathlib import Path
import docx
from backend.db import init_db
from backend.app.tools.documents.processor import doc_processor
from backend.app.tools.documents.tools import IndexDocumentTool, SearchDocumentsTool

@pytest.mark.anyio
async def test_document_indexing_and_rag_search(tmp_path):
    init_db()

    # 1. Create sample DOCX document
    docx_file = tmp_path / "architecture_guide.docx"
    doc = docx.Document()
    doc.add_heading("Personal AI Assistant V3 Architecture", 0)
    doc.add_paragraph("The V3 assistant features a modular ToolRegistry with strict permission checks.")
    doc.add_paragraph("Database connections run in read-only mode to prevent SQL injection.")
    doc.add_paragraph("Document chunks are indexed using vector embeddings and lexical search.")
    doc.save(str(docx_file))

    # 2. Mock embedding generation to test deterministically offline
    fake_vector = [0.1] * 768

    with patch("backend.ollama_client.embed_text", return_value=fake_vector):
        index_tool = IndexDocumentTool()
        res_idx = await index_tool.execute(
            file_path=str(docx_file),
            document_id="arch_guide_v3"
        )
        assert res_idx.success is True
        assert res_idx.data["chunks_indexed"] >= 1
        assert res_idx.data["document_id"] == "arch_guide_v3"

        # 3. Test SearchDocumentsTool
        search_tool = SearchDocumentsTool()
        res_search = await search_tool.execute(
            query="permission checks ToolRegistry",
            document_id="arch_guide_v3",
            top_k=2
        )
        assert res_search.success is True
        results = res_search.data["results"]
        assert len(results) >= 1
        top_match = results[0]
        assert "modular ToolRegistry with strict permission checks" in top_match["content"]
        assert top_match["filename"] == "architecture_guide.docx"
        assert len(res_search.metadata["citations"]) >= 1
        assert "architecture_guide.docx (p. 1)" in res_search.metadata["citations"][0]

