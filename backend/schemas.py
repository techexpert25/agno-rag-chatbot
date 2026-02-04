# backend/schemas.py
from pydantic import BaseModel
from typing import Optional

class UploadedFile(BaseModel):
    file_name: str
    file_path: str
    namespace: str
    created_at: Optional[str]

class FileUploadResponse(BaseModel):
    success: bool
    file: UploadedFile

class FileListResponse(BaseModel):
    files: list[UploadedFile]

class ChatStreamParams(BaseModel):
    q: str
    session_id: str
