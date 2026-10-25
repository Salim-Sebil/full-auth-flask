import pytest

from app import create_app
from extensions import db


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "JWT_SECRET_KEY": "test-secret-that-is-at-least-32-bytes-long",
        }
    )
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def signup(client, username="alice", password="password123"):
    response = client.post(
        "/auth/signup",
        json={"username": username, "password": password},
    )
    assert response.status_code == 201
    return response.get_json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_hashes_password_and_login_returns_jwt(client):
    response = client.post(
        "/auth/signup",
        json={"username": "Alice", "password": "password123"},
    )
    body = response.get_json()
    assert response.status_code == 201
    assert body["user"]["username"] == "alice"
    assert body["access_token"]

    with client.application.app_context():
        from models import User

        user = User.query.filter_by(username="alice").one()
        assert user.password_hash != "password123"
        assert user.check_password("password123")

    login = client.post(
        "/auth/login",
        json={"username": "ALICE", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.get_json()["user"]["id"] == body["user"]["id"]


def test_auth_validation_and_duplicate_username(client):
    assert client.post("/auth/signup", json={}).status_code == 400
    assert client.post(
        "/auth/signup",
        json={"username": "ééé", "password": "password123"},
    ).status_code == 400
    assert client.post(
        "/auth/signup",
        json={"username": "valid", "password": "é" * 40},
    ).status_code == 400
    signup(client)
    duplicate = client.post(
        "/auth/signup",
        json={"username": "ALICE", "password": "password123"},
    )
    assert duplicate.status_code == 409
    assert client.post(
        "/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    ).status_code == 401


def test_me_requires_valid_jwt_and_persists_user_identity(client):
    assert client.get("/auth/me").status_code == 401
    user = signup(client)["user"]
    token = client.post(
        "/auth/login",
        json={"username": "alice", "password": "password123"},
    ).get_json()["access_token"]
    response = client.get("/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.get_json()["user"] == user


def test_note_crud_and_pagination(client):
    token = signup(client)["access_token"]
    headers = auth_headers(token)
    created = client.post(
        "/notes",
        headers=headers,
        json={
            "title": "  First note  ",
            "content": "Text",
            "category": "work",
            "is_pinned": True,
        },
    )
    assert created.status_code == 201
    note = created.get_json()["note"]
    assert note["title"] == "First note"
    assert note["category"] == "work"

    second = client.post("/notes", headers=headers, json={"title": "Second"})
    assert second.status_code == 201
    listing = client.get("/notes?page=1&per_page=1", headers=headers).get_json()
    assert len(listing["notes"]) == 1
    assert listing["notes"][0]["id"] == note["id"]
    assert listing["pagination"] == {
        "page": 1,
        "per_page": 1,
        "total": 2,
        "pages": 2,
        "has_next": True,
        "has_prev": False,
    }

    updated = client.patch(
        f"/notes/{note['id']}",
        headers=headers,
        json={"title": "Updated", "is_pinned": False},
    )
    assert updated.status_code == 200
    assert updated.get_json()["note"]["title"] == "Updated"
    replaced = client.put(
        f"/notes/{note['id']}",
        headers=headers,
        json={"title": "Replaced"},
    )
    assert replaced.status_code == 200
    assert replaced.get_json()["note"]["content"] == ""
    assert replaced.get_json()["note"]["category"] == "general"
    assert client.get(f"/notes/{note['id']}", headers=headers).status_code == 200
    assert client.delete(f"/notes/{second.get_json()['note']['id']}", headers=headers).status_code == 204
    assert client.get("/notes", headers=headers).get_json()["pagination"]["total"] == 1


def test_notes_require_auth_and_are_isolated_by_user(client):
    alice_token = signup(client, "alice")["access_token"]
    bob_token = signup(client, "bob")["access_token"]
    created = client.post(
        "/notes",
        headers=auth_headers(alice_token),
        json={"title": "Private"},
    )
    note_id = created.get_json()["note"]["id"]

    assert client.get("/notes").status_code == 401
    assert client.get("/notes", headers=auth_headers(bob_token)).get_json()["notes"] == []
    assert client.get(
        f"/notes/{note_id}",
        headers=auth_headers(bob_token),
    ).status_code == 404
    assert client.patch(
        f"/notes/{note_id}",
        headers=auth_headers(bob_token),
        json={"title": "Stolen"},
    ).status_code == 404
    assert client.delete(
        f"/notes/{note_id}",
        headers=auth_headers(bob_token),
    ).status_code == 404


@pytest.mark.parametrize(
    "path",
    ["/notes?page=0", "/notes?page=nope", "/notes?per_page=0"],
)
def test_invalid_pagination_is_rejected(client, path):
    token = signup(client)["access_token"]
    response = client.get(path, headers=auth_headers(token))
    assert response.status_code == 400


def test_seed_command_creates_all_models_and_is_repeatable(client):
    runner = client.application.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0

    with client.application.app_context():
        from models import Note, User

        user = User.query.filter_by(username="demo").one()
        assert user.check_password("demo-password")
        assert Note.query.filter_by(user_id=user.id).count() == 2
