import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["ADMIN_EMAIL"] = "admin@test.co.mz"
os.environ["ADMIN_PASSWORD"] = "Admin@12345"

import pytest
from fastapi.testclient import TestClient

from app import models
from app.db import SessionLocal
from app.main import app


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def h(c):
    r = c.post("/api/auth/login", json={"email": "admin@test.co.mz", "password": "Admin@12345"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def lot(c, h):
    p = c.post("/api/producers", json={"name": "Coop Alfa", "province": "Gaza", "district": "Chókwè"}, headers=h).json()
    pr = c.post("/api/products", json={"name": "Tomate"}, headers=h).json()
    return c.post("/api/lots", json={"producer_id": p["id"], "product_id": pr["id"], "quantity": 50,
                                     "harvest_date": "2024-01-10"}, headers=h).json()


def test_qr_svg_is_public(c, lot):
    r = c.get(f"/api/lots/{lot['code']}/qr.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg") and b"<svg" in r.content
    assert c.get("/api/lots/NAOEXISTE/qr.svg").status_code == 404


def test_search_and_pagination(c, h, lot):
    for i in range(5):
        c.post("/api/producers", json={"name": f"Produtor {i}", "province": "Sofala"}, headers=h)
    page = c.get("/api/producers?limit=2&offset=0", headers=h).json()
    assert len(page["items"]) == 2 and page["total"] >= 6
    found = c.get("/api/producers?q=sofala", headers=h).json()
    assert found["total"] == 5
    assert c.get("/api/lots?q=tomate", headers=h).json()["total"] == 1
    assert c.get("/api/lots?q=zzz", headers=h).json()["total"] == 0


def test_edit_and_delete_lot(c, h, lot):
    body = {"producer_id": lot["producer"]["id"], "product_id": lot["product"]["id"], "quantity": 75,
            "harvest_date": "2024-01-10", "origin": "Chókwè"}
    r = c.put(f"/api/lots/{lot['id']}", json=body, headers=h)
    assert r.status_code == 200 and r.json()["quantity"] == 75
    new = c.post("/api/lots", json=body, headers=h).json()
    assert c.delete(f"/api/lots/{new['id']}", headers=h).status_code == 204
    d = c.post("/api/deliveries", json={"lot_id": lot["id"], "destination": "Beira"}, headers=h)
    assert d.status_code == 201
    assert c.put(f"/api/lots/{lot['id']}", json=body, headers=h).status_code == 409  # reservado
    assert c.delete(f"/api/lots/{lot['id']}", headers=h).status_code == 409


def test_user_management_and_password(c, h):
    u = c.post("/api/users", json={"name": "Op Um", "email": "op@test.co.mz", "password": "Operador@123",
                                   "role": "operador"}, headers=h).json()
    assert c.patch(f"/api/users/{u['id']}", json={"active": False}, headers=h).json()["active"] is False
    r = c.post("/api/auth/login", json={"email": "op@test.co.mz", "password": "Operador@123"})
    assert r.status_code == 401  # desactivado
    me = c.get("/api/auth/me", headers=h).json()
    assert c.patch(f"/api/users/{me['id']}", json={"active": False}, headers=h).status_code == 409
    bad = c.post("/api/auth/change-password", json={"current_password": "x", "new_password": "Nova@12345"}, headers=h)
    assert bad.status_code == 400
    ok = c.post("/api/auth/change-password", json={"current_password": "Admin@12345",
                                                   "new_password": "Nova@12345"}, headers=h)
    assert ok.status_code == 200
    assert c.post("/api/auth/login", json={"email": "admin@test.co.mz", "password": "Nova@12345"}).status_code == 200
    c.post("/api/auth/change-password", json={"current_password": "Nova@12345", "new_password": "Admin@12345"},
           headers=h)


def test_login_rate_limit(c):
    codes = [c.post("/api/auth/login", json={"email": "rl@test.co.mz", "password": "x"}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]


def test_audit_chain_detects_tampering(c, h):
    assert c.get("/api/audit/verify", headers=h).json()["valid"] is True
    with SessionLocal() as db:
        row = db.query(models.AuditLog).order_by(models.AuditLog.id).offset(2).first()
        row.detail = "ADULTERADO"
        db.commit()
        rid = row.id
    r = c.get("/api/audit/verify", headers=h).json()
    assert r["valid"] is False and r["broken_at"] == rid


def test_admin_created_even_if_other_users_exist():
    """Regressão: o seed cria o motorista antes da API arrancar; o admin tem de existir na mesma."""
    from sqlalchemy import select
    from app.security import hash_secret
    with SessionLocal() as db:
        admin = db.scalar(select(models.User).where(models.User.role == "admin"))
        assert admin is not None
