from app.services.doc_processor import DocumentProcessor


def make_processor(size=100, overlap=20):
    p = DocumentProcessor()
    p.chunk_size = size
    p.chunk_overlap = overlap
    return p


def test_empty_text_has_no_chunks():
    assert make_processor().split_into_chunks("") == []


def test_short_text_is_kept_as_single_chunk():
    assert make_processor().split_into_chunks("Tiny note.") == ["Tiny note."]


def test_chunks_cover_text_without_duplicate_tail():
    text = " ".join(f"Sentence number {i} is here." for i in range(60))
    chunks = make_processor().split_into_chunks(text)

    assert len(chunks) > 1
    assert chunks[-1].endswith("Sentence number 59 is here.")
    assert len(chunks) == len(set(chunks))
    # Every sentence ends up in some chunk
    for i in range(60):
        assert any(f"number {i} " in c for c in chunks)


def test_overlap_larger_than_chunk_size_still_terminates():
    chunks = make_processor(size=60, overlap=100).split_into_chunks("word " * 200)
    assert chunks


def test_txt_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("Hello café", encoding="utf-8")
    assert DocumentProcessor().extract_text(str(f)) == "Hello café"


def test_txt_utf16_with_bom(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("PostgreSQL is a database", encoding="utf-16")
    assert DocumentProcessor().extract_text(str(f)) == "PostgreSQL is a database"


def test_txt_windows_1252(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes("Price: 5€".encode("cp1252"))
    assert DocumentProcessor().extract_text(str(f)) == "Price: 5€"


def test_docx_includes_tables(tmp_path):
    from docx import Document

    d = Document()
    d.add_paragraph("Intro paragraph")
    table = d.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Skill"
    table.rows[0].cells[1].text = "Python"
    path = tmp_path / "t.docx"
    d.save(path)

    text = DocumentProcessor().extract_text(str(path))
    assert "Intro paragraph" in text
    assert "Skill | Python" in text
