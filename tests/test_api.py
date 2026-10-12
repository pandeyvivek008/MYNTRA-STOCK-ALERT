from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app

def login(client):
    response = client.post("/api/auth/login", json={"email":"admin@example.com", "password":"change-me-before-production"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_health_and_authentication():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/dashboard").status_code == 401
        assert client.post("/api/auth/login", json={"email":"admin@example.com", "password":"wrong"}).status_code == 401

def test_dashboard_and_product_catalogue():
    with TestClient(app) as client:
        headers = login(client)
        dashboard = client.get("/api/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["metrics"]["products"] >= 6
        product = client.get("/api/products", headers=headers).json()[0]
        detail = client.get(f"/api/products/{product['id']}", headers=headers)
        assert detail.status_code == 200
        assert len(detail.json()["variants"]) > 0

def test_csv_import_creates_product_and_alert():
    with TestClient(app) as client:
        headers = login(client)
        sku = f"TEST-{uuid4().hex[:10]}"
        data = f"sku,name,category,size,quantity,reorder_point\n{sku},Test Kurta,Women,M,0,5\n".encode()
        imported = client.post("/api/imports/inventory", headers=headers, files={"file":("inventory.csv",data,"text/csv")})
        assert imported.status_code == 200
        assert imported.json()["imported"] == 1
        assert imported.json()["new_alerts"] >= 1

def test_marketplace_order_reduces_colour_size_stock_once():
    with TestClient(app) as client:
        headers = {"X-Integration-Secret": "dev-webhook-secret-change-before-production"}
        payload = {"order_id": f"ORDER-{uuid4().hex}", "items":[{"sku":"MTR-KRT-1056","color":"Indigo","size":"M","quantity":2}]}
        processed = client.post("/api/integrations/myntra/orders", headers=headers, json=payload)
        assert processed.status_code == 200
        assert processed.json()["status"] == "processed"
        assert processed.json()["reductions"][0]["quantity"] == 5
        repeated = client.post("/api/integrations/myntra/orders", headers=headers, json=payload)
        assert repeated.json()["status"] == "already_processed"

def test_channels_and_unified_marketplace_endpoint():
    with TestClient(app) as client:
        headers = login(client)
        channels = client.get("/api/channels", headers=headers).json()
        assert {x["name"] for x in channels} == {"myntra","amazon","flipkart","ajio","nykaa","snapdeal"}
        payload = {"order_id": f"AMZ-{uuid4().hex}", "items":[{"sku":"MTR-TEE-1042","color":"Indigo","size":"S","quantity":1}]}
        result = client.post("/api/integrations/amazon/orders", headers={"X-Integration-Secret":"dev-webhook-secret-change-before-production"}, json=payload)
        assert result.status_code == 200
        assert result.json()["channel"] == "amazon"

def test_disha_answers_from_inventory():
    with TestClient(app) as client:
        response = client.post("/api/disha/query", headers=login(client), json={"query":"show critical stock alerts"})
        assert response.status_code == 200
        assert response.json()["action"] == "alerts"
        assert "variants" in response.json()["answer"]
