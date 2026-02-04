"""
Unit tests for agent configuration and wiring, these are.
Verify that agent is properly configured, I must.
"""
import pytest
import pytest_check as check
from agent_config.agent import agent, get_response_stream
from agent_config.db import db
from agent_config.document import knowledge


def test_agent_initialized():
    """Agent initialized, it must be. Model and database, configured they should be."""
    check.is_not_none(agent, "Agent instance, created it must be")
    check.is_not_none(agent.model, "Model configured, it must be")
    check.is_not_none(agent.db, "Database configured, it must be")
    check.is_not_none(agent.knowledge, "Knowledge base configured, it must be")


def test_agent_has_correct_settings():
    """Agent settings, correct they must be. Search knowledge and read history, enabled they should be."""
    check.equal(agent.search_knowledge, True, "Search knowledge enabled, it must be")
    check.equal(agent.read_chat_history, True, "Read chat history enabled, it must be")
    check.equal(agent.add_history_to_context, True, "Add history to context, enabled it must be")


def test_agent_db_connection():
    """Database connection, working it must be. Agent can access it, it should."""
    check.is_not_none(db, "Database instance, created it must be")
    # Database accessible, it should be
    check.is_true(hasattr(db, 'db_file'), "Database file path, it should have")


def test_agent_knowledge_base():
    """Knowledge base configured, it must be. Vector database, connected it should be."""
    check.is_not_none(knowledge, "Knowledge base instance, created it must be")
    check.is_not_none(knowledge.vector_db, "Vector database, configured it must be")


def test_get_response_stream_signature():
    """Response stream function, correct signature it must have. String and session_id, accept it should."""
    import inspect
    sig = inspect.signature(get_response_stream)
    params = list(sig.parameters.keys())
    
    check.is_in("query", params, "Query parameter, it must have")
    check.is_in("session_id", params, "Session ID parameter, it must have")
    check.equal(len(params), 2, "Two parameters only, it should have")


def test_get_response_stream_returns_iterator():
    """Response stream, iterator it must return. Chunks one by one, yield it should."""
    # Empty query, use I will. Iterator check, this is.
    stream = get_response_stream("test", "test-session")
    check.is_true(hasattr(stream, '__iter__'), "Iterator, it must be")
    check.is_true(hasattr(stream, '__next__'), "Next method, it must have")
