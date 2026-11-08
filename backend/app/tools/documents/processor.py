import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf
import docx
from backend.db import connect as connect_app_db
from backend.app.config import DOC_INDEX_DIR
import backend.ollama_client as ollama_client
from backend.memory import cosine, lexical_similarity

def parse_vector(val: Any) -> Optional[List[float]]:
    if not val:
        return None
    if isinstance(val, list):
        return val
    try:
        data = json.loads(val)
        return data if isinstance(data, list) else None
    except Exception:
        return None

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Parses PDF, DOCX, TXT, and Markdown files, chunks them, generates embeddings, and indexes them in SQLite."""

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extracts text sections/pages with metadata: [{'content': str, 'page_number': int}]"""
        ext = file_path.suffix.lower()
        sections = []

        if ext == ".pdf":
            reader = pypdf.PdfReader(str(file_path))
            for idx, page in enumerate(reader.pages, 1):
                txt = page.extract_text() or ""
                clean = txt.strip()
                if clean:
                    sections.append({"content": clean, "page_number": idx})
        elif ext == ".docx":
            doc = docx.Document(str(file_path))
            full_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    full_text.append(p.text.strip())
            joined = "\n\n".join(full_text)
            if joined:
                sections.append({"content": joined, "page_number": 1})
        elif ext in (".txt", ".md"):
            txt = file_path.read_text(encoding="utf-8", errors="replace").strip()
            if txt:
                sections.append({"content": txt, "page_number": 1})
        else:
            raise ValueError(f"Unsupported document format: {ext}")

        return sections

    def chunk_sections(
        self,
        sections: List[Dict[str, Any]],
        chunk_size: int = 800,
        overlap: int = 150
    ) -> List[Dict[str, Any]]:
        """Chunks document sections into overlapping sliding windows."""
        chunks = []
        chunk_idx = 0

        for sec in sections:
            text = sec["content"]
            page = sec.get("page_number", 1)

            # Split by paragraphs or sentences
            if len(text) <= chunk_size:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "content": text,
                    "page_number": page
                })
                chunk_idx += 1
                continue

            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                slice_text = text[start:end].strip()
                if slice_text:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "content": slice_text,
                        "page_number": page
                    })
                    chunk_idx += 1
                if end == len(text):
                    break
                start += (chunk_size - overlap)

        return chunks

    def index_document(self, doc_id: str, file_path: Path) -> int:
        """Parses, chunks, embeds, and saves document into database tables."""
        sections = self.parse_file(file_path)
        chunks = self.chunk_sections(sections)

        with connect_app_db() as c:
            # Register document entry
            c.execute(
                """
                INSERT INTO documents (id, filename, file_path, mime_type, size_bytes, status)
                VALUES (?, ?, ?, ?, ?, 'indexed')
                ON CONFLICT(id) DO UPDATE SET
                    filename=excluded.filename,
                    file_path=excluded.file_path,
                    size_bytes=excluded.size_bytes,
                    status='indexed'
                """,
                (doc_id, file_path.name, str(file_path.resolve()), file_path.suffix.lower(), file_path.stat().st_size)
            )

            # Clear old chunks if re-indexing
            c.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))

            # Embed and insert chunks
            for ch in chunks:
                vec = ollama_client.embed_text(ch["content"])
                vec_str = json.dumps(vec) if vec else ""
                c.execute(
                    """
                    INSERT INTO document_chunks (document_id, chunk_index, content, page_number, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (doc_id, ch["chunk_index"], ch["content"], ch["page_number"], vec_str)
                )

        return len(chunks)

    def search_chunks(self, query: str, document_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs hybrid vector & lexical similarity retrieval over indexed chunks."""
        query_vec = ollama_client.embed_text(query)
        results = []

        with connect_app_db() as c:
            sql = "SELECT c.*, d.filename FROM document_chunks c JOIN documents d ON c.document_id = d.id"
            params = []
            if document_id:
                sql += " WHERE c.document_id = ?"
                params.append(document_id)

            rows = c.execute(sql, tuple(params)).fetchall()

            for r in rows:
                content = r["content"]
                score = 0.0

                # 1. Lexical matching (keyword overlap)
                q_words = set(re.findall(r"\w+", query.lower()))
                c_words = set(re.findall(r"\w+", content.lower()))
                overlap = len(q_words & c_words) / max(len(q_words), 1)
                score += overlap * 0.4

                # 2. Vector cosine similarity if available
                if query_vec and r["embedding"]:
                    vec = parse_vector(r["embedding"])
                    if vec:
                        sim = cosine(query_vec, vec)
                        score += sim * 0.6

                results.append({
                    "document_id": r["document_id"],
                    "filename": r["filename"],
                    "chunk_index": r["chunk_index"],
                    "page_number": r["page_number"],
                    "content": content,
                    "score": round(score, 4)
                })

        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

doc_processor = DocumentProcessor()
