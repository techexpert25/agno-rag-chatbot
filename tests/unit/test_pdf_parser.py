"""
Unit tests for PDF parser, these are.
Real PDF files, test with I must.
"""
import pytest
import pytest_check as check
from pathlib import Path
from agent_config.document import handle_pdf_upload, UPLOAD_DIR
from agent_config.file_store import init_file_table, list_uploaded_files, delete_uploaded_file
import tempfile
import sqlite3
from agent_config.db import get_conn


@pytest.fixture
def temp_upload_dir(monkeypatch):
    """Temporary upload directory, set I do. Original path, override I will."""
    with tempfile.TemporaryDirectory() as tmpdir:
        upload_path = Path(tmpdir) / "uploads"
        upload_path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("agent_config.document.UPLOAD_DIR", upload_path)
        yield upload_path


@pytest.fixture
def temp_db(monkeypatch):
    """Temporary database, create I do. For file store tests, this is."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    # Monkeypatch the database path
    original_get_conn = get_conn
    def mock_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    monkeypatch.setattr("agent_config.file_store.get_conn", mock_get_conn)
    
    init_file_table()
    yield db_path
    if db_path.exists():
        db_path.unlink()


def create_minimal_pdf() -> bytes:
    """Minimal valid PDF, create I do. For testing, this is."""
    # PDF header and minimal structure, this is
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000306 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    return pdf_content


def test_handle_pdf_upload_valid_pdf(temp_upload_dir, temp_db):
    """Valid PDF upload, handle it I must. File saved and knowledge inserted, it should be."""
    pdf_content = create_minimal_pdf()
    result = handle_pdf_upload("test.pdf", pdf_content)
    
    check.is_not_none(result, "Result dictionary, returned it must be")
    check.is_in("document_id", result, "Document ID, it must contain")
    check.is_in("file_path", result, "File path, it must contain")
    check.is_in("file_name", result, "File name, it must contain")
    
    # File exists, it should
    file_path = Path(result["file_path"])
    check.is_true(file_path.exists(), "PDF file saved, it must be")
    check.equal(file_path.read_bytes(), pdf_content, "File content, correct it must be")


def test_handle_pdf_upload_creates_unique_document_id(temp_upload_dir, temp_db):
    """Document IDs, unique they must be. Each upload, different ID it should get."""
    pdf_content = create_minimal_pdf()
    result1 = handle_pdf_upload("test1.pdf", pdf_content)
    result2 = handle_pdf_upload("test2.pdf", pdf_content)
    
    check.not_equal(
        result1["document_id"],
        result2["document_id"],
        "Document IDs, different they must be"
    )


def test_handle_pdf_upload_saves_to_db(temp_upload_dir, temp_db):
    """File record, database it must save. List files, retrieve it should."""
    pdf_content = create_minimal_pdf()
    result = handle_pdf_upload("test.pdf", pdf_content)
    
    files = list_uploaded_files()
    check.greater(len(files), 0, "Files in database, at least one there should be")
    
    # Find our file, we must
    found = next((f for f in files if f["file_name"] == "test.pdf"), None)
    check.is_not_none(found, "Uploaded file, in database it should be")
    check.equal(found["namespace"], result["document_id"], "Namespace matches document ID, it must")


def test_handle_pdf_upload_rejects_non_pdf(temp_upload_dir, temp_db):
    """Non-PDF files, reject I must. ValueError, raise it should."""
    with pytest.raises(ValueError, match="Invalid PDF"):
        handle_pdf_upload("test.txt", b"not a pdf")


def test_handle_pdf_upload_rejects_empty_file(temp_upload_dir, temp_db):
    """Empty files, reject I must. ValueError, raise it should."""
    with pytest.raises(ValueError, match="Invalid PDF"):
        handle_pdf_upload("empty.pdf", b"")


def test_handle_pdf_upload_rejects_wrong_extension(temp_upload_dir, temp_db):
    """Wrong file extension, reject I must. Even if content looks like PDF, it should."""
    pdf_content = create_minimal_pdf()
    with pytest.raises(ValueError, match="Invalid PDF"):
        handle_pdf_upload("test.docx", pdf_content)


def test_pdf_parser_with_real_file(sample_pdf_path, temp_upload_dir, temp_db):
    """Real PDF file, parse it I must. Content extracted, it should be."""
    pdf_content = sample_pdf_path.read_bytes()
    result = handle_pdf_upload(sample_pdf_path.name, pdf_content)
    
    check.is_not_none(result, "Result, returned it must be")
    check.is_true(Path(result["file_path"]).exists(), "File saved, it must be")
    
    # File size, reasonable it should be
    file_size = Path(result["file_path"]).stat().st_size
    check.greater(file_size, 0, "File size, greater than zero it must be")
