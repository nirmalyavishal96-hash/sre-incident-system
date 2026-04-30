from fastapi import FastAPI, Request
from app.database import engine, Base, redis_client, SessionLocal
import app.models
from app.models import Incident, RCA
from app.schemas import StatusUpdate, RCACreate
from datetime import datetime
import json
import time
import threading
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)


# Metrics (Signals/sec)

signal_count = 0
start_time = time.time()

def log_metrics():
    global signal_count, start_time

    while True:
        time.sleep(5)
        elapsed = time.time() - start_time
        rate = signal_count / elapsed if elapsed > 0 else 0
        print(f"Signals/sec: {rate:.2f}")

threading.Thread(target=log_metrics, daemon=True).start()


# Rate Limiting

rate_limit_store = {}
RATE_LIMIT = 5   # requests
WINDOW = 10      # seconds


@app.get("/")
def root():
    return {"message": "IMS Backend Running"}



# Health Check

@app.get("/health")
def health():
    return {"status": "ok"}



# Ingestion API (with rate limit)

@app.post("/ingest")
def ingest_signal(payload: dict, request: Request):
    global signal_count

    client_ip = request.client.host
    now = time.time()

    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []

    # Remove old timestamps
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < WINDOW
    ]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        return {"error": "Rate limit exceeded"}

    rate_limit_store[client_ip].append(now)

    # Push to queue
    redis_client.rpush("signal_queue", json.dumps(payload))
    signal_count += 1

    return {"status": "queued"}



# Get Incidents (with MTTR)

@app.get("/incidents")
def get_incidents():
    db = SessionLocal()
    incidents = db.query(Incident).all()

    result = []
    for i in incidents:
        mttr = None
        if i.resolved_at:
            mttr = (i.resolved_at - i.created_at).total_seconds()

        result.append({
            "id": i.id,
            "component": i.component,
            "status": i.status,
            "created_at": i.created_at,
            "resolved_at": i.resolved_at,
            "mttr_seconds": mttr
        })

    db.close()
    return result



# Update Incident Status

@app.put("/incidents/{incident_id}/status")
def update_status(incident_id: int, payload: StatusUpdate):
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    # ❗ Enforce RCA before closing
    if payload.status == "CLOSED":
        if not incident.rca:
            db.close()
            return {"error": "Cannot close incident without RCA"}

        incident.resolved_at = datetime.utcnow()

    incident.status = payload.status
    db.commit()
    db.refresh(incident)

    db.close()
    return {"message": "Status updated", "status": incident.status}



# Add RCA

@app.post("/incidents/{incident_id}/rca")
def add_rca(incident_id: int, payload: RCACreate):
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    new_rca = RCA(
        incident_id=incident_id,
        root_cause=payload.root_cause,
        fix=payload.fix
    )

    db.add(new_rca)
    db.commit()

    db.close()
    return {"message": "RCA added"}