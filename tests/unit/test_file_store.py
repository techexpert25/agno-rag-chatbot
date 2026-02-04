"""
Unit tests for file store operations, these are.
Database operations, test I must.
"""
import pytest
import pytest_check as check
from pathlib import Path
import sqlite3
import tempfile
from agent_config.file_store import (
    init_file_table,
    save_file_record,
    list_uploaded_files,
    delete_uploaded_file,
)
from agent_config.db import get_conn


@pytest.fixture
def temp_db(monkeypatch):
    """Temporary database, create I do. For testing, this is."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    # Monkeypatch get_conn to use our temp DB
    def mock_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    monkeypatch.setattr("agent_config.file_store.get_conn", mock_get_conn)
    
    yield db_path
    
    if db_path.exists():
        db_path.unlink()


def test_init_file_table_creates_table(temp_db):
    """File table, create it I must. Schema correct, it should be."""
    init_file_table()
    
    # Use get_conn to verify, I must
    with get_conn() as conn:
        cursor = conn.cursor()
        
        # Table exists, check I must
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='uploaded_documents'
        """)
        result = cursor.fetchone()
        check.is_not_none(result, "Table created, it must be")
        
        # Columns, verify I must
        cursor.execute("PRAGMA table_info(uploaded_documents)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        check.is_in("file_name", columns, "file_name column, it must have")
        check.is_in("file_path", columns, "file_path column, it must have")
        check.is_in("pinecone_namespace", columns, "pinecone_namespace column, it must have")
        check.is_in("created_at", columns, "created_at column, it must have")


def test_save_file_record_inserts_data(temp_db):
    """File record, save it I must. Database, insert into it I should."""
    init_file_table()
    
    save_file_record(
        file_name="test.pdf",
        file_path="/tmp/test.pdf",
        pinecone_namespace="doc_123",
    )
    
    files = list_uploaded_files()
    check.equal(len(files), 1, "One file record, there should be")
    check.equal(files[0]["file_name"], "test.pdf", "File name, correct it must be")
    check.equal(files[0]["namespace"], "doc_123", "Namespace, correct it must be")


def test_list_uploaded_files_returns_all(temp_db):
    """List files, all return it must. Multiple records, handle it should."""
    init_file_table()
    
    # Multiple records, insert I must
    save_file_record("file1.pdf", "/tmp/file1.pdf", "doc_1")
    save_file_record("file2.pdf", "/tmp/file2.pdf", "doc_2")
    save_file_record("file3.pdf", "/tmp/file3.pdf", "doc_3")
    
    files = list_uploaded_files()
    check.equal(len(files), 3, "Three files, there should be")
    
    # File names, verify I must
    file_names = [f["file_name"] for f in files]
    check.is_in("file1.pdf", file_names, "file1.pdf, in list it should be")
    check.is_in("file2.pdf", file_names, "file2.pdf, in list it should be")
    check.is_in("file3.pdf", file_names, "file3.pdf, in list it should be")


def test_list_uploaded_files_empty_when_no_files(temp_db):
    """Empty list, return I must. No files, empty list it should return."""
    init_file_table()
    
    files = list_uploaded_files()
    check.equal(len(files), 0, "Empty list, it must return")


def test_delete_uploaded_file_removes_record(temp_db):
    """Delete file record, remove it I must. Database and file, delete it should."""
    init_file_table()
    
    # Create a temporary file, I must
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_path = Path(tmp.name)
        file_path.write_bytes(b"test content")
    
    save_file_record("test.pdf", str(file_path), "doc_delete_test")
    
    # Delete, I must
    result = delete_uploaded_file("doc_delete_test")
    check.is_true(result, "Delete, success it must return")
    
    # File removed from DB, verify I must
    files = list_uploaded_files()
    check.equal(len(files), 0, "No files, there should be")
    
    # File removed from disk, verify I must
    check.is_false(file_path.exists(), "File on disk, deleted it should be")


def test_delete_uploaded_file_nonexistent_returns_none(temp_db):
    """Nonexistent file, delete gracefully I must. None, return it should."""
    init_file_table()
    
    result = delete_uploaded_file("nonexistent_doc")
    check.is_none(result, "Nonexistent file, None it must return")
