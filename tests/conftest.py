"""
Shared fixtures for tests, I provide.
Test database and temporary files, create I do.
Isolated from production, tests must be.
"""
import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="function", autouse=True)
def isolate_test_environment(monkeypatch, tmp_path):
    """
    Isolate test environment, I must. 
    Production database and media folder, use not I will.
    Temporary paths, all tests shall use.
    """
    # Temporary database path, create I do
    test_db_path = tmp_path / "test_app.db"
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Temporary upload directory, create I do
    test_upload_dir = tmp_path / "media" / "uploads"
    test_upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Database path, override I must
    try:
        import agent_config.db as db_module
        
        def mock_get_conn():
            """Mock database connection, temporary path it uses."""
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            return conn
        
        monkeypatch.setattr("agent_config.db.get_conn", mock_get_conn)
        monkeypatch.setattr("agent_config.db.APP_DB_PATH", test_db_path)
        
        # Also patch file_store module
        monkeypatch.setattr("agent_config.file_store.get_conn", mock_get_conn)
        
        # Agno database, also override I must
        if hasattr(db_module, 'db') and hasattr(db_module.db, 'db_file'):
            monkeypatch.setattr(db_module.db, "db_file", str(test_db_path))
    except (ImportError, AttributeError):
        pass
    
    # Upload directory, override I must
    try:
        import agent_config.document as doc_module
        monkeypatch.setattr("agent_config.document.UPLOAD_DIR", test_upload_dir)
    except ImportError:
        pass
    
    yield {
        "db_path": test_db_path,
        "upload_dir": test_upload_dir
    }
    
    # Cleanup, perform I must
    try:
        if test_db_path.exists():
            test_db_path.unlink()
        
        if test_upload_dir.exists():
            shutil.rmtree(test_upload_dir, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """Temporary database path, create I do. Clean up after test, I will."""
    db_path = tmp_path / "test.db"
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_db_conn(temp_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Test database connection, provide I do. Row factory set, I have."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def test_upload_dir(tmp_path) -> Path:
    """Temporary upload directory, create I do. Clean up after test, I will."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    yield upload_dir


@pytest.fixture
def sample_pdf_path() -> Path:
    """Path to sample PDF, return I do. In tests/data, it lives."""
    pdf_path = Path(__file__).parent / "data" / "sample.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found at {pdf_path}")
    return pdf_path


@pytest.fixture
def sample_pdf_content(sample_pdf_path: Path) -> bytes:
    """Sample PDF content as bytes, read I do."""
    return sample_pdf_path.read_bytes()


@pytest.fixture
def mock_openai_key(monkeypatch):
    """Mock OpenAI API key, set I do. For tests that need it, this is."""
    test_key = os.getenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", test_key)
    return test_key
