import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from .database import Base, SessionLocal, engine, get_db
from .live import hub
from .models import Alert, Product, Variant
from .security import create_token, verify_token
from .settings import settings

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "FREE SIZE"]

def variant_state(v: Variant):
    if v.quantity <= 0: return "out"
    if v.quantity <= max(1, v.reorder_point // 2): return "critical"
    if v.quantity <= v.reorder_point: return "low"
    return "healthy"

def product_json(p: Product):
    variants = sorted(p.variants, key=lambda x: SIZE_ORDER.index(x.size.upper()) if x.size.upper() in SIZE_ORDER else 99)
    stock = sum(v.quantity for v in variants)
    states = [variant_state(v) for v in variants]
    status = "out" if stock == 0 else "critical" if "critical" in states or "out" in states else "low" if "low" in states else "healthy"
    return {"id":p.id,"sku":p.sku,"name":p.name,"category":p.category,"image_url":p.image_url,"updated_at":p.updated_at.isoformat() if p.updated_at else None,"total_stock":stock,"status":status,"variants":[{"id":v.id,"size":v.size,"quantity":v.quantity,"reorder_point":v.reorder_point,"state":variant_state(v)} for v in variants]}

def alert_json(a: Alert):
    return {"id":a.id,"severity":a.severity,"status":a.status,"message":a.message,"created_at":a.created_at.isoformat(),"product":{"id":a.product.id,"sku":a.product.sku,"name":a.product.name},"variant":{"id":a.variant.id,"size":a.variant.size,"quantity":a.variant.quantity}}

def auth_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "Sign in required")
    return verify_token(authorization.split(" ", 1)[1])

def issue_alert_if_needed(db: Session, product: Product, variant: Variant):
    state = variant_state(variant)
    if state == "healthy": return None
    existing = db.scalar(select(Alert).where(Alert.variant_id == variant.id, Alert.status.in_(["open", "acknowledged"])))
    if existing: return None
    severity = "out_of_stock" if state == "out" else "critical" if state == "critical" else "low"
    alert = Alert(product_id=product.id, variant_id=variant.id, severity=severity, message=f"{product.name} · {variant.size} has {variant.quantity} units left (reorder point: {variant.reorder_point}).")
    db.add(alert); db.flush()
    return alert

def seed(db: Session):
    if db.scalar(select(func.count(Product.id))): return
    records = [
        ("MTR-TEE-1042", "Everyday Supima T-Shirt", "Men · T-shirts", [12, 7, 4, 9, 2]),
        ("MTR-KRT-1056", "Indigo Blockprint Kurta", "Women · Kurtas", [12, 7, 4, 9, 2]),
        ("MTR-DNM-2088", "Relaxed Fit Denim", "Men · Jeans", [18, 12, 8, 3, 0]),
        ("MTR-DRS-3110", "Ribbed Midi Dress", "Women · Dresses", [7, 5, 2, 1, 0]),
        ("MTR-SHR-4412", "Linen Blend Shirt", "Men · Shirts", [25, 18, 13, 11, 8]),
        ("MTR-SET-5199", "Printed Co-ord Set", "Women · Sets", [4, 2, 0, 6, 3]),
    ]
    for sku, name, category, levels in records:
        p = Product(sku=sku, name=name, category=category); db.add(p); db.flush()
        for size, quantity in zip(["S", "M", "L", "XL", "XXL"], levels):
            v = Variant(product_id=p.id, size=size, quantity=quantity, reorder_point=5); db.add(v); db.flush(); issue_alert_if_needed(db,p,v)
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield

app = FastAPI(title="Myntra Stock Watch", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/api/health")
def health(): return {"status":"ok", "service":"myntra-stock-watch"}

@app.post("/api/auth/login")
def login(body: dict):
    if body.get("email", "").lower() != settings.admin_email.lower() or body.get("password") != settings.admin_password:
        raise HTTPException(401, "Invalid email or password")
    return {"access_token":create_token(settings.admin_email), "token_type":"bearer", "user":{"email":settings.admin_email,"role":"inventory-manager"}}

@app.get("/api/dashboard")
def dashboard(_: str = Depends(auth_user), db: Session = Depends(get_db)):
    products = db.scalars(select(Product).options(joinedload(Product.variants))).unique().all()
    alerts = db.scalars(select(Alert).options(joinedload(Alert.product),joinedload(Alert.variant)).where(Alert.status != "resolved").order_by(Alert.created_at.desc()).limit(8)).unique().all()
    variants = [v for p in products for v in p.variants]
    return {"metrics":{"products":len(products),"units":sum(v.quantity for v in variants),"low_stock":sum(variant_state(v)=="low" for v in variants),"critical":sum(variant_state(v) in ["critical","out"] for v in variants),"open_alerts":len(alerts)},"alerts":[alert_json(a) for a in alerts],"products":[product_json(p) for p in products]}

@app.get("/api/products")
def products(query: str = "", status: str = "all", _: str = Depends(auth_user), db: Session = Depends(get_db)):
    statement = select(Product).options(joinedload(Product.variants)).order_by(Product.updated_at.desc())
    if query: statement = statement.where(or_(Product.name.ilike(f"%{query}%"), Product.sku.ilike(f"%{query}%"), Product.category.ilike(f"%{query}%")))
    result = [product_json(p) for p in db.scalars(statement).unique().all()]
    return [p for p in result if status == "all" or p["status"] == status]

@app.get("/api/products/{product_id}")
def product(product_id: int, _: str = Depends(auth_user), db: Session = Depends(get_db)):
    p = db.scalar(select(Product).options(joinedload(Product.variants)).where(Product.id==product_id))
    if not p: raise HTTPException(404, "Product not found")
    return product_json(p)

@app.get("/api/alerts")
def alerts(status: str = "open", _: str = Depends(auth_user), db: Session = Depends(get_db)):
    q = select(Alert).options(joinedload(Alert.product),joinedload(Alert.variant)).order_by(Alert.created_at.desc())
    if status != "all": q = q.where(Alert.status == status)
    return [alert_json(a) for a in db.scalars(q).unique().all()]

@app.patch("/api/alerts/{alert_id}")
async def update_alert(alert_id: int, body: dict, _: str = Depends(auth_user), db: Session = Depends(get_db)):
    alert = db.scalar(select(Alert).options(joinedload(Alert.product),joinedload(Alert.variant)).where(Alert.id==alert_id))
    if not alert: raise HTTPException(404,"Alert not found")
    status = body.get("status")
    if status not in ["open","acknowledged","resolved"]: raise HTTPException(422,"status must be open, acknowledged or resolved")
    alert.status = status; db.commit(); db.refresh(alert)
    payload = {"type":"alert_updated","alert":alert_json(alert)}; await hub.broadcast(payload)
    return payload["alert"]

@app.post("/api/imports/inventory")
async def import_inventory(file: UploadFile = File(...), _: str = Depends(auth_user), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"): raise HTTPException(415, "Upload a CSV file")
    try: rows = list(csv.DictReader(io.StringIO((await file.read()).decode("utf-8-sig"))))
    except UnicodeDecodeError: raise HTTPException(422,"CSV must be UTF-8 encoded")
    needed = {"sku","name","category","size","quantity","reorder_point"}
    if not rows or not needed.issubset(rows[0]): raise HTTPException(422, f"Required columns: {', '.join(sorted(needed))}")
    changed = []; created_alerts = []
    for row in rows:
        try: quantity, point = int(row["quantity"]), int(row["reorder_point"])
        except ValueError: raise HTTPException(422, f"Invalid numbers for SKU {row['sku']}")
        if quantity < 0 or point < 0: raise HTTPException(422,"Quantity and reorder point cannot be negative")
        p = db.scalar(select(Product).where(Product.sku==row["sku"].strip()))
        if not p:
            p=Product(sku=row["sku"].strip(),name=row["name"].strip(),category=row["category"].strip()); db.add(p); db.flush()
        else: p.name=row["name"].strip() or p.name; p.category=row["category"].strip() or p.category
        v = db.scalar(select(Variant).where(Variant.product_id==p.id,Variant.size==row["size"].strip().upper()))
        if not v: v=Variant(product_id=p.id,size=row["size"].strip().upper(),quantity=quantity,reorder_point=point); db.add(v); db.flush()
        else: v.quantity=quantity; v.reorder_point=point
        db.flush(); changed.append({"sku":p.sku,"size":v.size,"quantity":v.quantity,"state":variant_state(v)})
        alert=issue_alert_if_needed(db,p,v)
        if alert: created_alerts.append(alert)
    db.commit()
    for alert in created_alerts:
        db.refresh(alert, attribute_names=["product","variant"]); await hub.broadcast({"type":"alert_created","alert":alert_json(alert)})
    await hub.broadcast({"type":"inventory_imported","rows":len(rows),"changed":changed})
    return {"imported":len(rows),"new_alerts":len(created_alerts),"changed":changed}

@app.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket, token: str = Query(...)):
    try: verify_token(token)
    except HTTPException: await websocket.close(code=1008); return
    await hub.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: hub.disconnect(websocket)

@app.get("/")
def index(): return FileResponse("app/static/index.html")
