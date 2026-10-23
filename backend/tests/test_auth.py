def test_register_login_and_successful_login_audit(client):
    registration = {
        "name": "Test User",
        "email": "test.user@example.com",
        "password": "SecureTest123!",
    }

    register_response = client.post(
        "/api/auth/register",
        json=registration,
    )

    assert register_response.status_code == 201
    registered_user = register_response.json()
    assert registered_user["email"] == "test.user@example.com"
    assert registered_user["role"] == "viewer"
    assert registered_user["is_active"] is True

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "TEST.USER@example.com",
            "password": "SecureTest123!",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token
    assert login_response.json()["token_type"] == "bearer"

    audit_response = client.get(
        "/api/audit/my-events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert audit_response.status_code == 200
    events = audit_response.json()
    assert any(event["action"] == "auth.login" for event in events)


def test_duplicate_registration_is_rejected(client):
    registration = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "SecureTest123!",
    }

    first_response = client.post(
        "/api/auth/register",
        json=registration,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/auth/register",
        json=registration,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "An account with this email already exists"
    )




def test_inactive_user_cannot_login(client):
    registration = {
        "name": "Inactive User",
        "email": "inactive@example.com",
        "password": "SecureTest123!",
    }

    register_response = client.post(
        "/api/auth/register",
        json=registration,
    )
    assert register_response.status_code == 201

    # Use only the isolated in-memory test database.
    TestingSessionLocal = client.app.state.TestingSessionLocal
    from app.models.user import User

    with TestingSessionLocal() as db:
        user = db.query(User).filter_by(
            email="inactive@example.com"
        ).first()
        assert user is not None
        user.is_active = False
        db.commit()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "SecureTest123!",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == (
        "Invalid email or password"
    )


def test_viewer_cannot_access_admin_endpoints(client):
    registration = {
        "name": "Viewer User",
        "email": "viewer@example.com",
        "password": "SecureTest123!",
    }

    register_response = client.post(
        "/api/auth/register",
        json=registration,
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "viewer@example.com",
            "password": "SecureTest123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    users_response = client.get(
        "/api/admin/users",
        headers=headers,
    )
    assert users_response.status_code == 403

    audit_response = client.get(
        "/api/admin/audit/last-24-hours",
        headers=headers,
    )
    assert audit_response.status_code == 403

    assert users_response.json()["detail"] == (
        "Administrator privileges required"
    )
    assert audit_response.json()["detail"] == (
        "Administrator privileges required"
    )


def test_users_can_only_view_their_own_audit_events(client):
    first_token = client.post(
        "/api/auth/register",
        json={
            "name": "First Audit User",
            "email": "first-audit@example.com",
            "password": "SecureTest123!",
        },
    )
    assert first_token.status_code == 201

    first_login = client.post(
        "/api/auth/login",
        json={
            "email": "first-audit@example.com",
            "password": "SecureTest123!",
        },
    )
    assert first_login.status_code == 200
    first_headers = {
        "Authorization": f"Bearer {first_login.json()['access_token']}"
    }

    second_register = client.post(
        "/api/auth/register",
        json={
            "name": "Second Audit User",
            "email": "second-audit@example.com",
            "password": "SecureTest123!",
        },
    )
    assert second_register.status_code == 201

    second_login = client.post(
        "/api/auth/login",
        json={
            "email": "second-audit@example.com",
            "password": "SecureTest123!",
        },
    )
    assert second_login.status_code == 200
    second_headers = {
        "Authorization": f"Bearer {second_login.json()['access_token']}"
    }

    first_events = client.get(
        "/api/audit/my-events", headers=first_headers
    )
    second_events = client.get(
        "/api/audit/my-events", headers=second_headers
    )

    assert first_events.status_code == 200
    assert second_events.status_code == 200

    assert any(
        event["action"] == "auth.login"
        for event in first_events.json()
    )
    assert any(
        event["action"] == "auth.login"
        for event in second_events.json()
    )

    assert all(
        event["actor_id"] == first_token.json()["id"]
        for event in first_events.json()
    )
    assert all(
        event["actor_id"] == second_register.json()["id"]
        for event in second_events.json()
    )
