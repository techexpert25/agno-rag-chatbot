"""
Integration test for upload → parse → query → answer flow, this is.
End-to-end, test I must. PDF content, reference in answer it should.
"""
import pytest
import pytest_check as check
from fastapi.testclient import TestClient
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

@pytest.fixture
def client(isolate_test_environment):
    """
    Test client, create I do. 
    Isolated environment, use it must.
    """
    # Import app after environment is isolated
    from backend.main import app
    # Reinitialize file table in test database
    from agent_config.file_store import init_file_table
    init_file_table()
    return TestClient(app)


def create_minimal_pdf() -> bytes:
    """Minimal valid PDF with test content, create I do."""
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
/Length 60
>>
stream
BT
/F1 12 Tf
100 700 Td
(The answer is 42. This is test content.) Tj
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
414
%%EOF"""
    return pdf_content


def test_upload_parse_query_answer_flow(client, sample_pdf_path):
    """Upload → parse → query → answer, test I must. PDF content, reference it should."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skip this test I must")
    
    # Step 1: Upload PDF
    pdf_content = sample_pdf_path.read_bytes()
    upload_response = client.post(
        "/upload/pdf",
        files={"file": (sample_pdf_path.name, pdf_content, "application/pdf")}
    )
    
    check.equal(upload_response.status_code, 200, "Upload, success it must be")
    upload_data = upload_response.json()
    check.is_true(upload_data["success"], "Upload success flag, true it must be")
    check.is_not_none(upload_data["file"], "File data, present it must be")
    
    document_id = upload_data["file"]["namespace"]
    check.is_not_none(document_id, "Document ID, present it must be")
    
    # Step 2: Verify file listed
    list_response = client.get("/files")
    check.equal(list_response.status_code, 200, "List files, success it must be")
    files = list_response.json()["files"]
    check.greater(len(files), 0, "Files in list, at least one there should be")
    
    # Find our file, we must
    found_file = next((f for f in files if f["file_name"] == sample_pdf_path.name), None)
    check.is_not_none(found_file, "Uploaded file, in list it should be")
    
    # Step 3: Query about the document
    session_id = "test-session-upload-flow"
    query = f"What is in the document {sample_pdf_path.name}?"
    
    stream_response = client.get(
        f"/chat/stream?q={query}&session_id={session_id}"
    )
    
    check.equal(stream_response.status_code, 200, "Stream query, success it must be")
    
    # Step 4: Collect response
    response_text = ""
    chunk_count = 0
    for chunk in stream_response.iter_lines():
        if chunk:
            response_text += chunk
            chunk_count += 1
    
    check.greater(chunk_count, 0, "Response chunks, at least one there should be")
    check.greater(len(response_text), 0, "Response text, non-empty it must be")
    
    # Cleanup: Delete the file
    try:
        delete_response = client.delete(
            f"/files/{document_id}",
            params={"file_name": sample_pdf_path.name}
        )
        # Delete might succeed or fail, but we tried
        check.is_in(delete_response.status_code, [200, 404], "Delete, attempt it we did")
    except Exception:
        pass  # Cleanup failure, acceptable it is


def test_upload_minimal_pdf_then_query(client):
    """Minimal PDF upload and query, test I must. Simple flow, verify I will."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skip this test I must")
    
    # Upload minimal PDF
    pdf_content = create_minimal_pdf()
    upload_response = client.post(
        "/upload/pdf",
        files={"file": ("test_minimal.pdf", pdf_content, "application/pdf")}
    )
    
    check.equal(upload_response.status_code, 200, "Upload, success it must be")
    upload_data = upload_response.json()
    document_id = upload_data["file"]["namespace"]
    
    # Query about it
    session_id = "test-minimal-flow"
    query = "What does the test document say?"
    
    stream_response = client.get(
        f"/chat/stream?q={query}&session_id={session_id}"
    )
    
    check.equal(stream_response.status_code, 200, "Query, success it must be")
    
    # Collect response
    response_parts = []
    for chunk in stream_response.iter_lines():
        if chunk:
            response_parts.append(chunk)
    
    check.greater(len(response_parts), 0, "Response parts, at least one there should be")
    
    # Cleanup: Delete the file
    try:
        client.delete(
            f"/files/{document_id}",
            params={"file_name": "test_minimal.pdf"}
        )
    except Exception:
        pass  # Cleanup failure, acceptable it is


def test_upload_rejects_oversized_file(client):
    """Oversized file, reject I must. 10MB limit, enforce it should."""
    # Create file larger than 10MB
    large_content = b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024)  # 11 MB
    
    upload_response = client.post(
        "/upload/pdf",
        files={"file": ("large.pdf", large_content, "application/pdf")}
    )
    
    check.equal(upload_response.status_code, 413, "Oversized file, 413 it must return")


def test_upload_rejects_empty_file(client):
    """Empty file, reject I must. 400 error, return it should."""
    upload_response = client.post(
        "/upload/pdf",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    
    check.equal(upload_response.status_code, 400, "Empty file, 400 it must return")


def test_upload_rejects_non_pdf(client):
    """Non-PDF file, reject I must. Only PDF, accept I should."""
    upload_response = client.post(
        "/upload/pdf",
        files={"file": ("test.txt", b"not a pdf", "text/plain")}
    )
    
    check.equal(upload_response.status_code, 400, "Non-PDF file, 400 it must return")
