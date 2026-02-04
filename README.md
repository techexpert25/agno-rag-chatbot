# RAG Chatbot with FastAPI, Agno, and NiceGUI

A minimal Document QA Chatbot that streams agent responses, supports PDF uploads, and provides async status signals in the UI.

## Architecture Overview

This application follows a clean separation of concerns:

- **FastAPI Backend** (`backend/`): Handles API endpoints, streaming, file uploads, and business logic
- **Agno Agent** (`agent_config/`): Orchestrates LLM interactions, knowledge base queries, and session management
- **NiceGUI Frontend** (`app.py`): Thin UI layer that visualizes backend operations and handles user interactions


### Installation

```bash
# Clone the repository
git clone <repository-url>
cd AgnoNiceGUI_PythonChallenge

# (Optional) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install project and dev dependencies via pyproject.toml
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env  # or create .env manually
# Edit .env and add your OPENAI_API_KEY, PINECONE_API_KEY, and INDEX_NAME
```

### Running the Application

You can either run backend and frontend separately (more explicit for debugging), or use the combined helper script.

```bash
# Option 1: run services separately

# Terminal 1: FastAPI backend (with auto-reload)
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: NiceGUI frontend
python app.py

# Option 2: run both via helper script (FastAPI + NiceGUI together)
./run.sh
```

The application will be available at:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Test Structure

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
  - Agent configuration and wiring
  - PDF parser with real sample files
  - Error handling (corrupt/empty/oversized files)
  - File store database operations

- **Integration Tests** (`tests/integration/`): Test end-to-end flows
  - Streaming endpoint with multiple chunks
  - Upload → parse → query → answer flow

- **Test Data** (`tests/data/`): Real PDF files for testing


## Cursor Configuration

This project is configured to maximize productivity with Cursor AI IDE. Here's how it's set up:

### MCP Servers

**Agno Documentation**: Configured to access Agno docs for agent configuration, session management, and knowledge base features. This helps ensure we're using Agno's built-in capabilities correctly rather than reinventing functionality.

**FastAPI Documentation**: FastAPI docs are indexed for quick reference on streaming responses, dependency injection, and Pydantic model usage.

**NiceGUI Documentation**: NiceGUI docs are available for UI component reference and async event handling patterns.

### .cursorrules File

A `.cursorrules` file is included in the project root that provides:
- Project context and architecture overview
- Code style guidelines (modern typing, Pydantic preference)
- Testing conventions
- Important reminders (Yoda-style comments, no secrets in git)

This helps Cursor understand the project's conventions and generate code that fits the existing patterns.


## API Endpoints

### `POST /chat/stream`
- Streams agent responses token-by-token.

### `POST /upload/pdf`
- Uploads and indexes a PDF document.

### `GET /files`
- Lists all uploaded documents.

### `DELETE /files/{document_id}`
- Deletes an uploaded document from database, disk, and Pinecone.


## Environment Variables

Create a `.env` file (or copy `.env.example`) and set:

```env
# OpenAI configuration
OPENAI_API_KEY=your_openai_api_key

# Pinecone configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name

# Backend base URL used by the NiceGUI frontend (e.g. http://localhost:8000)
FASTAPI_API_BASE=your_fastapi_domain_name

# Comma-separated list of allowed frontend origins for CORS (e.g. http://localhost:8080)
ALLOW_ORIGINS=[]
```

## License

This project is part of a coding challenge assessment.
