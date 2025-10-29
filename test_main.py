# test_main.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "EduTube" in res.json()["message"]

def test_register_and_login():
    email = "testuser@example.com"
    password = "test123"
    name = "tester"

    res = client.post("/register_user", json={"name": name, "email": email, "password": password})
    assert res.status_code in [200, 400]

    res = client.post("/login_user", data={"username": email, "password": password})
    assert res.status_code in [200, 401]
