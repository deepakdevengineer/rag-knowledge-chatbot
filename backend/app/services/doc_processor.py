"""
Document Processor — Extract text from PDF, TXT, DOCX and split into chunks
"""
from pathlib import Path
from app.config import settings

# Encodings tried, in order, when reading plain-text files
TXT_ENCODINGS = ("utf-8-sig", "utf-16", "cp1252")


class DocumentProcessor:
    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def extract_text(self, filepath: str) -> str:
        """Extract text from a file based on its extension."""
        ext = Path(filepath).suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(filepath)
        elif ext == ".txt":
            return self._extract_txt(filepath)
        elif ext == ".docx":
            return self._extract_docx(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, filepath: str) -> str:
        """Extract text from PDF."""
        from pypdf import PdfReader

        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        return text.strip()

    def _extract_txt(self, filepath: str) -> str:
        """Extract text from TXT file, detecting UTF-8 / UTF-16 (BOM) / Windows-1252."""
        raw = Path(filepath).read_bytes()
        # UTF-16 without a BOM can't be detected reliably, so only try it when a BOM is present
        encodings = TXT_ENCODINGS if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "cp1252")
        for enc in encodings:
            try:
                return raw.decode(enc).replace("\x00", "").strip()
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore").replace("\x00", "").strip()

    def _extract_docx(self, filepath: str) -> str:
        """Extract text from DOCX file — paragraphs and tables."""
        from docx import Document

        doc = Document(filepath)
        parts = [para.text for para in doc.paragraphs if para.text.strip()]

        # Tables are not part of doc.paragraphs; read them row by row
        for table in doc.tables:
            for row in table.rows:
                cells = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Merged cells repeat the same text across the row
                    if cell_text and cell_text not in cells:
                        cells.append(cell_text)
                if cells:
                    parts.append(" | ".join(cells))

        return "\n\n".join(parts).strip()

    def split_into_chunks(self, text: str) -> list[str]:
        """Split text into overlapping chunks (sizes in characters) for better retrieval."""
        if not text:
            return []

        chunks = []
        start = 0
        prev_end = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # Try to break at a sentence boundary
            if end < text_length:
                # Look for sentence endings near the chunk boundary
                for sep in ["\n\n", ".\n", ". ", "\n"]:
                    last_sep = text.rfind(sep, start + self.chunk_size // 2, end + 100)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk and len(chunk) > 50:
                chunks.append(chunk)
            elif chunk and chunks:
                # Too small to stand alone — merge into the previous chunk instead of losing it
                new_part = text[max(start, prev_end):end].strip()
                if new_part:
                    chunks[-1] = f"{chunks[-1]} {new_part}"
            prev_end = end

            if end >= text_length:
                break
            # Always move forward, even if the overlap is misconfigured (>= chunk size)
            start = max(end - self.chunk_overlap, start + 1)

        # A very short document is still worth indexing as a single chunk
        if not chunks and text.strip():
            chunks.append(text.strip())

        return chunks

    def process_file(self, filepath: str) -> list[str]:
        """Full pipeline: extract text from file and split into chunks."""
        text = self.extract_text(filepath)
        if not text:
            return []
        chunks = self.split_into_chunks(text)
        return chunks


# Singleton instance
doc_processor = DocumentProcessor()
