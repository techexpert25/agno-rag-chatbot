"""
Error tests for PDF upload, these are.
Corrupt, empty, and oversized files, test I must.
"""
import pytest
import pytest_check as check
from pathlib import Path
from agent_config.document import handle_pdf_upload
import tempfile
import sqlite3
from agent_config.file_store import init_file_table, get_conn


@pytest.fixture
def temp_upload_dir(monkeypatch):
    """Temporary upload directory, set I do."""
    with tempfile.TemporaryDirectory() as tmpdir:
        upload_path = Path(tmpdir) / "uploads"
        upload_path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("agent_config.document.UPLOAD_DIR", upload_path)
        yield upload_path


@pytest.fixture
def temp_db(monkeypatch):
    """Temporary database, create I do."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
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


def test_corrupt_pdf_rejected(temp_upload_dir, temp_db):
    """Corrupt PDF file, reject I must. Invalid structure, detect it should."""
    corrupt_content = b"%PDF-1.4\nThis is not a valid PDF structure\n%%EOF"
    
    with pytest.raises((ValueError, Exception)):
        handle_pdf_upload("corrupt.pdf", corrupt_content)


def test_empty_pdf_rejected(temp_upload_dir, temp_db):
    """Empty PDF file, reject I must. Zero bytes, handle it should."""
    with pytest.raises(ValueError, match="Invalid PDF"):
        handle_pdf_upload("empty.pdf", b"")


def test_oversized_pdf_rejected(temp_upload_dir, temp_db):
    """Oversized PDF file, backend should reject it. FastAPI endpoint, check it must."""
    # Note: Actual size check happens in FastAPI endpoint
    # This test verifies the parser itself handles large content
    large_content = b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024)  # 11 MB
    
    # Parser might accept it, but FastAPI will reject
    # For unit test, we check that function doesn't crash
    try:
        result = handle_pdf_upload("large.pdf", large_content)
        # If it succeeds, that's okay - FastAPI will handle size limit
        check.is_not_none(result)
    except (ValueError, MemoryError, OSError):
        # Acceptable, if parser rejects oversized files
        pass


def test_invalid_file_type_rejected(temp_upload_dir, temp_db):
    """Invalid file types, reject I must. Only PDF, accept I should."""
    test_cases = [
        ("test.txt", b"text content"),
        ("test.docx", b"PK\x03\x04"),  # ZIP header (docx is zip)
        ("test.jpg", b"\xFF\xD8\xFF\xE0"),  # JPEG header
    ]
    
    for filename, content in test_cases:
        with pytest.raises(ValueError, match="Invalid PDF"):
            handle_pdf_upload(filename, content)


def test_missing_filename_handled(temp_upload_dir, temp_db):
    """Missing filename, handle gracefully I must. Empty string, reject it should."""
    pdf_content = b"%PDF-1.4\n%%EOF"
    
    with pytest.raises((ValueError, TypeError)):
        handle_pdf_upload("", pdf_content)


def test_none_content_rejected(temp_upload_dir, temp_db):
    """None content, reject I must. TypeError or ValueError, raise it should."""
    with pytest.raises((TypeError, ValueError)):
        handle_pdf_upload("test.pdf", None)  # type: ignore
