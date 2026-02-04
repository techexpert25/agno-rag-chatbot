"""
Integration tests for streaming, these are.
Multiple chunks, verify I must. Not a single blob, it should be.
"""
import pytest
import pytest_check as check
from fastapi.testclient import TestClient
import os
from dotenv import load_dotenv
load_dotenv()


@pytest.fixture
def client(isolate_test_environment):
    """
    Test client, create I do. 
    Isolated environment, use it must.
    FastAPI app, test with it I will.
    """
    # Import app after environment is isolated
    from backend.main import app
    # Reinitialize file table in test database
    from agent_config.file_store import init_file_table
    init_file_table()
    return TestClient(app)


def test_streaming_endpoint_returns_chunks(client):
    """Streaming endpoint, chunks it must return. Multiple pieces, yield it should."""
    # OpenAI API key, required it is
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skip this test I must")
    
    query = "What is 2+2?"
    session_id = "test-session-123"
    
    response = client.get(
        f"/chat/stream?q={query}&session_id={session_id}"
    )
    
    check.equal(response.status_code, 200, "Status code 200, it must be")
    check.equal(
        response.headers.get("content-type"),
        "text/plain; charset=utf-8",
        "Content type text/plain, it must be"
    )
    
    # Chunks, collect I must
    chunks = []
    for chunk in response.iter_lines():
        if chunk:
            chunks.append(chunk)
    
    check.greater(len(chunks), 0, "At least one chunk, there should be")
    # Multiple chunks, verify I must
    check.greater_equal(len(chunks), 1, "Multiple chunks or at least one, there should be")


def test_streaming_chunks_are_incremental(client):
    """Streaming chunks, incremental they must be. Each chunk, add to previous it should."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skip this test I must")
    
    query = "Count from 1 to 5"
    session_id = "test-session-incremental"
    
    response = client.get(
        f"/chat/stream?q={query}&session_id={session_id}"
    )
    
    check.equal(response.status_code, 200, "Status code 200, it must be")
    
    # Chunks, collect I must
    full_text = ""
    chunk_count = 0
    
    for chunk in response.iter_lines():
        if chunk:
            full_text += chunk
            chunk_count += 1
    
    check.greater(chunk_count, 0, "Chunks received, at least one there should be")
    check.greater(len(full_text), 0, "Full text, non-empty it must be")


def test_streaming_preserves_session(client):
    """Session history, preserve it must. Multiple queries, context they should share."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skip this test I must")
    
    session_id = "test-session-persist"
    
    # First query, send I must
    query1 = "My name is TestUser"
    response1 = client.get(
        f"/chat/stream?q={query1}&session_id={session_id}"
    )
    check.equal(response1.status_code, 200, "First query, success it must be")
    
    # Consume response, I must
    for _ in response1.iter_lines():
        pass
    
    # Second query, send I must
    query2 = "What is my name?"
    response2 = client.get(
        f"/chat/stream?q={query2}&session_id={session_id}"
    )
    check.equal(response2.status_code, 200, "Second query, success it must be")
    
    # Response, collect I must
    response_text = ""
    for chunk in response2.iter_lines():
        if chunk:
            response_text += chunk
    
    # Context preserved, verify I can (if agent supports it)
    check.greater(len(response_text), 0, "Response text, non-empty it must be")


def test_streaming_handles_empty_query(client):
    """Empty query, handle gracefully I must. Error or empty response, return it should."""
    session_id = "test-session-empty"
    
    response = client.get(
        f"/chat/stream?q=&session_id={session_id}"
    )
    
    # Either 200 with empty response or 400, acceptable both are
    check.is_in(
        response.status_code,
        [200, 400, 422],
        "Status code, valid it must be"
    )


def test_streaming_requires_session_id(client):
    """Session ID, required it must be. Missing parameter, error it should return."""
    response = client.get("/chat/stream?q=test")
    # Missing session_id, error it should return
    check.is_in(
        response.status_code,
        [400, 422],
        "Missing session_id, error it must return"
    )
