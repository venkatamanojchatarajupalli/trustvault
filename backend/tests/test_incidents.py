from app.models.document import Document
from app.models.user import User


PASSWORD = "SecureTest123!"


def register_user(client, email, name="Test User"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text


def login(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def create_admin(client, email):
    register_user(client, email, "Test Administrator")

    testing_session = client.app.state.TestingSessionLocal
    with testing_session() as db:
        user = db.query(User).filter_by(email=email).first()
        assert user is not None
        user.role = "admin"
        admin_id = user.id
        db.commit()

    return login(client, email), admin_id


def create_test_document(client, owner_id):
    testing_session = client.app.state.TestingSessionLocal
    with testing_session() as db:
        document = Document(
            owner_id=owner_id,
            title="Incident test document",
            storage_key="incident-test.txt",
            sha256="a" * 64,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document.id


def test_viewer_cannot_create_incident(client):
    email = "incident-viewer@example.com"
    register_user(client, email)
    token = login(client, email)

    response = client.post(
        "/api/admin/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_id": 999,
            "description": "Suspicious document access detected",
        },
    )

    assert response.status_code == 403


def test_admin_can_create_incident_for_existing_document(client):
    token, admin_id = create_admin(
        client, "incident-admin@example.com"
    )
    document_id = create_test_document(client, admin_id)

    response = client.post(
        "/api/admin/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_id": document_id,
            "description": "Suspicious document access detected",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document_id"] == document_id
    assert body["reported_by"] == admin_id
    assert body["description"] == "Suspicious document access detected"
    assert body["status"] == "open"


def test_admin_cannot_create_incident_for_missing_document(client):
    token, _ = create_admin(
        client, "incident-admin-missing@example.com"
    )

    response = client.post(
        "/api/admin/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_id": 999999,
            "description": "Suspicious document access detected",
        },
    )

    assert response.status_code == 404
