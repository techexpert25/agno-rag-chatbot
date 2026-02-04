from pathlib import Path
from os import getenv
from uuid import uuid4

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb
from .file_store import save_file_record
from dotenv import load_dotenv
load_dotenv()

index_name = getenv("PINECONE_INDEX_NAME")

vector_db = PineconeDb(
    name=index_name,
    dimension=1536,
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
)

knowledge = Knowledge(
    name="My Pinecone Knowledge Base",
    description="PDF-backed knowledge base",
    vector_db=vector_db,
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "media" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def handle_pdf_upload(file_name: str, content: bytes) -> dict:
    if not file_name.lower().endswith(".pdf") or not content:
        raise ValueError("Invalid PDF")

    document_id = f"doc_{uuid4().hex}"
    stored_name = f"{document_id}_{file_name}"
    file_path = UPLOAD_DIR / stored_name

    with open(file_path, "wb") as f:
        f.write(content)

    knowledge.insert(
        name=document_id,
        path=str(file_path),
        metadata={
            "document_id": document_id,
            "source": file_name,
        },
        skip_if_exists=True,
    )

    save_file_record(
        file_name=file_name,
        file_path=str(file_path),
        pinecone_namespace=document_id,  # reuse column
    )

    return {
        "document_id": document_id,
        "file_path": str(file_path),
        "file_name": file_name,
    }


def handle_delete_pdf(file_name):
    try:
        vector_db.delete_by_metadata({"source": file_name})
        return True
    except Exception as e:
        print(f"error deleting pincoin data for {file_name} :",str(e))
        return False


