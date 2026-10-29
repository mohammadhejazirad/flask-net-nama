import pytest
from netnama import create_app


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": tmp_path})
    yield app
    app.extensions["scheduler"].close()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client):
    import re

    text = client.get("/auth/login").get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', text)[1]


@pytest.fixture
def login(client):
    token = csrf(client)
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "123456"}, headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    return {"X-CSRFToken": csrf(client)}
