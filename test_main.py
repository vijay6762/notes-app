import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(client, username, password):
    client.post("/register", json={"username": username, "password": password})
    r = client.post("/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_happy_path(client):
    h = make_user(client, "vijay", "secret123")

    r = client.post("/notes", json={"title": "Milk", "content": "2 l"}, headers=h)
    assert r.status_code == 201
    note_id = r.json()["id"]
    assert "owner_id" not in r.json()

    assert len(client.get("/notes", headers=h).json()) == 1

    r = client.patch(f"/notes/{note_id}", json={"content": "5 l"}, headers=h)
    assert r.json()["title"] == "Milk"
    assert r.json()["content"] == "5 l"

    assert client.delete(f"/notes/{note_id}", headers=h).status_code == 204
    assert client.get(f"/notes/{note_id}", headers=h).status_code == 404


def test_unauthenticated_rejected(client):
    assert client.get("/notes").status_code == 401
    assert client.post("/notes", json={"title": "x"}).status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/notes", headers=bad).status_code == 401


def test_user_b_cannot_touch_user_a_note(client):
    a = make_user(client, "vijay", "secret123")
    b = make_user(client, "asha", "secret456")

    note_id = client.post("/notes", json={"title": "Private"}, headers=a).json()["id"]

    assert client.get("/notes", headers=b).json() == []
    assert client.get(f"/notes/{note_id}", headers=b).status_code == 404
    assert client.patch(f"/notes/{note_id}", json={"title": "Hacked"}, headers=b).status_code == 404
    assert client.delete(f"/notes/{note_id}", headers=b).status_code == 404

    # vijay's note is still there and unchanged
    r = client.get(f"/notes/{note_id}", headers=a)
    assert r.status_code == 200
    assert r.json()["title"] == "Private"