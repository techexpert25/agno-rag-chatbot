import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from .db import get_conn


def init_file_table() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                pinecone_namespace TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_file_record(
    file_name: str,
    file_path: str,
    pinecone_namespace: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO uploaded_documents
            (file_name, file_path, pinecone_namespace, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                file_name,
                file_path,
                pinecone_namespace,
                datetime.utcnow().isoformat(),
            ),
        )


def list_uploaded_files() -> List[Dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT file_name, file_path, pinecone_namespace, created_at
            FROM uploaded_documents
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "file_name": row["file_name"],
            "file_path": row["file_path"],
            "namespace": row["pinecone_namespace"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]



def delete_uploaded_file(document_id: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT file_path
            FROM uploaded_documents
            WHERE pinecone_namespace = ?
            """,
            (document_id,),
        ).fetchone()

        if not row:
            return None

        conn.execute(
            """
            DELETE FROM uploaded_documents
            WHERE pinecone_namespace = ?
            """,
            (document_id,),
        )
        conn.commit()

    Path(row["file_path"]).unlink(missing_ok=True)
    return True

