import os
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Path,
    Query
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from agent_config.file_store import init_file_table, list_uploaded_files, delete_uploaded_file
from agent_config.document import handle_pdf_upload ,handle_delete_pdf
from agent_config.agent import get_response_stream
from .schemas import UploadedFile, FileListResponse, ChatStreamParams, FileUploadResponse
from dotenv import load_dotenv
load_dotenv()
app = FastAPI()

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOW_ORIGINS').split(' '),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_file_table()


@app.get(
    "/files",
    response_model=FileListResponse,
    summary="List uploaded documents",
)
def get_uploaded_files():
    files = list_uploaded_files()
    return {"files": files}


@app.post(
    "/upload/pdf",
    response_model=FileUploadResponse,
    summary="Upload PDF document",
)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name missing")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_FILE_SIZE_MB} MB allowed",
        )

    result = handle_pdf_upload(
        file_name=file.filename,
        content=content,
    )

    uploaded_file = UploadedFile(
        file_name=file.filename,
        file_path=result["file_path"],
        namespace=result.get("namespace", "default"),
        created_at=datetime.utcnow().isoformat(),
    )

    return FileUploadResponse(
        success=True,
        file=uploaded_file,
    )


@app.delete(
    "/files/{document_id}",
    summary="Delete uploaded file (DB + disk + Pinecone)",
)
def delete_file(
    document_id: str = Path(..., description="Document ID"),
    file_name: str = Query(..., description="Original file name"),
):
    # 1️⃣ delete DB + disk using document_id
    file_deleted = delete_uploaded_file(document_id)

    if not file_deleted:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # 2️⃣ delete Pinecone vectors using document_id
    pinecone_deleted = handle_delete_pdf(file_name)

    if not pinecone_deleted:
        # not fatal, but worth logging
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return {
        "success": True,
        "document_id": document_id,
        "file_name": file_name,
        "message": f"{file_name} deleted successfully",
    }


@app.post(
    "/chat/stream",
    summary="Stream chat response",
)
def chat_stream(params: ChatStreamParams):
    return StreamingResponse(
        get_response_stream(params.q, params.session_id),
        media_type="text/plain",
    )
