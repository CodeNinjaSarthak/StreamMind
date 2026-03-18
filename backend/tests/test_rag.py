"""Black-box contract tests for RAG document endpoints.

Endpoint paths (from backend/app/api/v1/rag.py + main.py mount):
  POST   /api/v1/rag/documents       — upload (multipart, field name "file")
  GET    /api/v1/rag/documents        — list owned documents
  DELETE /api/v1/rag/documents/{id}   — delete owned document (204)

Upload calls upload_document() which invokes GeminiClient.generate_embedding
— that is already patched to None by the client fixture (QueueManager.enqueue
is stubbed), but we also need to patch the Gemini call inside upload_document.
"""

import io
import uuid
from unittest.mock import patch

from httpx import AsyncClient


async def test_upload_document_appears_in_list(client: AsyncClient, auth_headers: dict):
    """Upload a small PDF → 2xx → GET list → document appears in response."""
    pdf_content = b"%PDF-1.4 fake pdf content with enough words " + b"word " * 50

    with (
        patch("app.services.rag.document_service.GeminiClient") as mock_gemini_cls,
        patch("app.services.rag.document_service._extract_text_pdf", return_value="Some test content " * 50),
    ):
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.generate_embedding.return_value = [0.1] * 768

        resp = await client.post(
            "/api/v1/rag/documents",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chunks_created"] >= 1
    assert len(body["document_ids"]) >= 1

    # Verify it appears in the list
    list_resp = await client.get("/api/v1/rag/documents", headers=auth_headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()
    uploaded_ids = set(body["document_ids"])
    listed_ids = {d["id"] for d in docs}
    assert uploaded_ids.issubset(listed_ids)


async def test_teacher_only_sees_own_documents(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    """Teacher A uploads → Teacher B lists → Teacher B sees 0 documents."""
    pdf_content = b"%PDF-1.4 fake pdf content with enough words " + b"word " * 50

    with (
        patch("app.services.rag.document_service.GeminiClient") as mock_gemini_cls,
        patch("app.services.rag.document_service._extract_text_pdf", return_value="Some test content " * 50),
    ):
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.generate_embedding.return_value = [0.1] * 768

        await client.post(
            "/api/v1/rag/documents",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_headers,
        )

    # Teacher B should see nothing
    list_resp = await client.get("/api/v1/rag/documents", headers=second_auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json() == []


async def test_delete_document_removes_it_from_list(client: AsyncClient, auth_headers: dict):
    """Upload → delete → list → document gone."""
    pdf_content = b"%PDF-1.4 fake pdf content with enough words " + b"word " * 50

    with (
        patch("app.services.rag.document_service.GeminiClient") as mock_gemini_cls,
        patch("app.services.rag.document_service._extract_text_pdf", return_value="Some test content " * 50),
    ):
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.generate_embedding.return_value = [0.1] * 768

        resp = await client.post(
            "/api/v1/rag/documents",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_headers,
        )

    doc_id = resp.json()["document_ids"][0]

    del_resp = await client.delete(f"/api/v1/rag/documents/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/rag/documents", headers=auth_headers)
    listed_ids = {d["id"] for d in list_resp.json()}
    assert doc_id not in listed_ids


async def test_delete_nonexistent_document_returns_404(client: AsyncClient, auth_headers: dict):
    """DELETE with random UUID → 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/rag/documents/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_teacher_b_cannot_delete_teacher_a_document(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    """Teacher A uploads → Teacher B tries to delete → 404 (ownership boundary)."""
    pdf_content = b"%PDF-1.4 fake pdf content with enough words " + b"word " * 50

    with (
        patch("app.services.rag.document_service.GeminiClient") as mock_gemini_cls,
        patch("app.services.rag.document_service._extract_text_pdf", return_value="Some test content " * 50),
    ):
        mock_gemini = mock_gemini_cls.return_value
        mock_gemini.generate_embedding.return_value = [0.1] * 768

        resp = await client.post(
            "/api/v1/rag/documents",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_headers,
        )

    doc_id = resp.json()["document_ids"][0]

    # Teacher B tries to delete Teacher A's document
    del_resp = await client.delete(f"/api/v1/rag/documents/{doc_id}", headers=second_auth_headers)
    assert del_resp.status_code == 404


async def test_upload_invalid_file_type_is_rejected(client: AsyncClient, auth_headers: dict):
    """Upload a .exe file → 415 (unsupported media type)."""
    resp = await client.post(
        "/api/v1/rag/documents",
        files={"file": ("malware.exe", io.BytesIO(b"MZ fake exe"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 415
