import pytest


def create_user(client, name, email, password="SecureTest123!"):
    registration = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert registration.status_code == 201, registration.text

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text

    return login.json()["access_token"]


def upload_document(client, token, title="Security test document"):
    response = client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": title},
        files={"file": ("security-test.txt", b"Private test content", "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_only_owner_can_share_document(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Owner User", "owner@example.com"
    )
    other_token = create_user(
        client, "Other User", "other@example.com"
    )

    document = upload_document(client, owner_token)
    document_id = document["id"]

    response = client.post(
        f"/api/documents/{document_id}/share",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"email": "owner@example.com", "can_edit": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_owner_cannot_share_document_with_self(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Owner User", "self-owner@example.com"
    )
    document = upload_document(client, owner_token)

    response = client.post(
        f"/api/documents/{document['id']}/share",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "self-owner@example.com", "can_edit": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You already own this document"


def test_denied_download_is_audited(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Document Owner", "audit-owner@example.com"
    )
    viewer_token = create_user(
        client, "Document Viewer", "audit-viewer@example.com"
    )

    document = upload_document(client, owner_token)

    download = client.get(
        f"/api/documents/{document['id']}/download",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert download.status_code == 404

    audit_response = client.get(
        "/api/audit/my-events",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert audit_response.status_code == 200
    assert any(
        event["action"] == "document.access_denied"
        for event in audit_response.json()
    )


def test_download_permission_is_revoked_immediately(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Share Owner", "share-owner@example.com"
    )
    viewer_token = create_user(
        client, "Share Viewer", "share-viewer@example.com"
    )

    document = upload_document(client, owner_token)
    document_id = document["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    share_response = client.post(
        f"/api/documents/{document_id}/share",
        headers=owner_headers,
        json={"email": "share-viewer@example.com", "can_edit": False},
    )
    assert share_response.status_code == 201, share_response.text
    permission_id = share_response.json()["id"]

    allowed_download = client.get(
        f"/api/documents/{document_id}/download",
        headers=viewer_headers,
    )
    assert allowed_download.status_code == 200
    assert allowed_download.content == b"Private test content"

    revoke_response = client.delete(
        f"/api/documents/{document_id}/share/{permission_id}",
        headers=owner_headers,
    )
    assert revoke_response.status_code in (200, 204), revoke_response.text

    denied_download = client.get(
        f"/api/documents/{document_id}/download",
        headers=viewer_headers,
    )
    assert denied_download.status_code == 404



def test_upload_rejects_unsupported_file_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)
    token = create_user(
        client, "Upload Tester", "invalid-file@example.com"
    )

    response = client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "Unsupported file"},
        files={"file": ("malware.exe", b"test content", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "File type not allowed"
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_oversized_file_and_cleans_up(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)
    token = create_user(
        client, "Large Upload Tester", "large-file@example.com"
    )

    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "Oversized file"},
        files={"file": ("oversized.txt", oversized_content, "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File exceeds the 10 MiB limit"
    assert list(tmp_path.iterdir()) == []

def test_private_document_is_not_listed_to_another_user(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "List Owner", "list-owner@example.com"
    )
    other_token = create_user(
        client, "List Other", "list-other@example.com"
    )

    document = upload_document(client, owner_token)

    response = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200, response.text
    assert all(
        item["id"] != document["id"]
        for item in response.json()
    )


def test_only_owner_can_list_document_permissions(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Permissions Owner", "permissions-owner@example.com"
    )
    other_token = create_user(
        client, "Permissions Other", "permissions-other@example.com"
    )

    document = upload_document(client, owner_token)

    response = client.get(
        f"/api/documents/{document['id']}/permissions",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_only_owner_can_revoke_document_permission(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.documents.STORAGE_DIR", tmp_path)

    owner_token = create_user(
        client, "Revoke Owner", "revoke-owner@example.com"
    )
    recipient_token = create_user(
        client, "Revoke Recipient", "revoke-recipient@example.com"
    )
    other_token = create_user(
        client, "Revoke Other", "revoke-other@example.com"
    )

    document = upload_document(client, owner_token)

    share_response = client.post(
        f"/api/documents/{document['id']}/share",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "email": "revoke-recipient@example.com",
            "can_edit": False,
        },
    )
    assert share_response.status_code == 201, share_response.text

    permission_id = share_response.json()["id"]

    response = client.delete(
        f"/api/documents/{document['id']}/share/{permission_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404

    recipient_download = client.get(
        f"/api/documents/{document['id']}/download",
        headers={"Authorization": f"Bearer {recipient_token}"},
    )
    assert recipient_download.status_code == 200
    assert recipient_download.content == b"Private test content"
