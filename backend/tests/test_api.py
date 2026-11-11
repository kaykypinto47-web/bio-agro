import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["ADMIN_EMAIL"] = "admin@test.co.mz"
os.environ["ADMIN_PASSWORD"] = "Admin@12345"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth(c, email="admin@test.co.mz", pw="Admin@12345"):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_wrong_password(client):
    assert client.post("/api/auth/login", json={"email": "admin@test.co.mz", "password": "x"}).status_code == 401


def test_requires_auth(client):
    assert client.get("/api/producers").status_code == 401


def test_full_flow(client):
    h = auth(client)
    p = client.post("/api/producers", json={"name": "Coop Teste", "province": "Maputo"}, headers=h).json()
    pr = client.post("/api/products", json={"name": "Milho", "unit": "kg"}, headers=h).json()
    assert client.post("/api/products", json={"name": "Milho"}, headers=h).status_code == 409

    bad = client.post("/api/lots", json={"producer_id": p["id"], "product_id": pr["id"], "quantity": 10,
                                         "harvest_date": "2999-01-01"}, headers=h)
    assert bad.status_code == 422
    lot = client.post("/api/lots", json={"producer_id": p["id"], "product_id": pr["id"], "quantity": 250,
                                         "harvest_date": "2024-05-01", "origin": "Boane"}, headers=h).json()

    client.post("/api/users", json={"name": "Mot", "email": "m@test.co.mz", "password": "Motor@1234",
                                    "role": "motorista"}, headers=h)
    drivers = [u for u in client.get("/api/users", headers=h).json() if u["role"] == "motorista"]
    d = client.post("/api/deliveries", json={"lot_id": lot["id"], "destination": "Mercado Zimpeto",
                                             "driver_id": drivers[0]["id"]}, headers=h).json()
    code = d["confirmation_code"]
    assert len(code) == 6 and "confirmation_code_hash" not in d

    # lote já em entrega não pode ter outra
    assert client.post("/api/deliveries", json={"lot_id": lot["id"], "destination": "X1"}, headers=h).status_code == 409
    # confirmar antes de iniciar trânsito falha
    assert client.post(f"/api/deliveries/{d['id']}/confirm",
                       json={"code": code, "receiver_name": "Ana"}, headers=h).status_code == 409

    mh = auth(client, "m@test.co.mz", "Motor@1234")
    assert client.post(f"/api/deliveries/{d['id']}/status", json={"status": "em_transito"}, headers=mh).status_code == 200
    wrong = "000000" if code != "000000" else "111111"
    assert client.post(f"/api/deliveries/{d['id']}/confirm",
                       json={"code": wrong, "receiver_name": "Ana"}, headers=mh).status_code == 400
    ok = client.post(f"/api/deliveries/{d['id']}/confirm", json={"code": code, "receiver_name": "Ana"}, headers=mh)
    assert ok.status_code == 200 and ok.json()["status"] == "entregue"

    t = client.get(f"/api/trace/{lot['code']}").json()  # público
    assert t["status"] == "entregue" and [e["status"] for e in t["timeline"]][-1] == "entregue"
    assert client.get("/api/stats", headers=h).json()["deliveries_done"] == 1
    assert len(client.get("/api/audit", headers=h).json()) > 5
    assert client.get("/api/audit", headers=mh).status_code == 403


def test_driver_cannot_create(client):
    mh = auth(client, "m@test.co.mz", "Motor@1234")
    assert client.post("/api/producers", json={"name": "Zé", "province": "Gaza"}, headers=mh).status_code == 403
