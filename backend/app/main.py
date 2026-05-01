from fastapi import FastAPI, Request
from app.database import engine, Base, redis_client, SessionLocal
import app.models
from app.models import Incident, RCA
from app.schemas import StatusUpdate, RCACreate
from datetime import datetime
import json
import time
import threading

# Prometheus
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from fastapi.middleware.cors import CORSMiddleware

# STATE MACHINE
VALID_TRANSITIONS = {
    "OPEN": ["INVESTIGATING"],
    "INVESTIGATING": ["RESOLVED"],
    "RESOLVED": ["CLOSED"],
    "CLOSED": []
}

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Setup
Base.metadata.create_all(bind=engine)


# PROMETHEUS METRICS


REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API Requests",
    ["method", "endpoint", "status"]
)

SIGNAL_COUNT = Counter(
    "signals_total",
    "Total signals received",
    ["type"]
)

QUEUE_SIZE = Gauge(
    "queue_size",
    "Current Redis queue size"
)

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"]
)


# MIDDLEWARE


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status_code
        ).inc()

        latency = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(latency)

        raise

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=status_code
    ).inc()

    latency = time.time() - start_time
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(latency)

    return response


# SIGNAL RATE LOGGER


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


# RATE LIMITING


rate_limit_store = {}
RATE_LIMIT = 5
WINDOW = 10


# BASIC ROUTES


@app.get("/")
def root():
    return {"message": "IMS Backend Running"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "queue_size": redis_client.llen("signal_queue")
    }

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# INGESTION API


@app.post("/ingest")
def ingest_signal(payload: dict, request: Request):
    global signal_count

    SIGNAL_COUNT.labels(type="incoming").inc()

    client_ip = request.client.host
    now = time.time()

    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []

    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < WINDOW
    ]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        return {"error": "Rate limit exceeded"}

    rate_limit_store[client_ip].append(now)

    redis_client.rpush("signal_queue", json.dumps(payload))

    QUEUE_SIZE.set(redis_client.llen("signal_queue"))

    signal_count += 1

    return {"status": "queued"}


# INCIDENTS


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
            "severity": i.severity,
            "created_at": i.created_at,
            "resolved_at": i.resolved_at,
            "mttr_seconds": mttr
        })

    db.close()
    return result


# UPDATE STATUS (FIXED)


@app.put("/incidents/{incident_id}/status")
def update_status(incident_id: int, payload: StatusUpdate):
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    current_status = incident.status
    new_status = payload.status

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        db.close()
        return {
            "error": f"Invalid transition from {current_status} to {new_status}"
        }

    # RCA enforcement before closing
    if new_status == "CLOSED":
        if not incident.rca or not incident.rca.root_cause or not incident.rca.fix:
            db.close()
            return {"error": "Complete RCA required before closing"}

    # Set resolved_at ONLY once
    if new_status == "RESOLVED" and not incident.resolved_at:
        incident.resolved_at = datetime.utcnow()

    incident.status = new_status
    print(f"[STATUS CHANGE] Incident {incident.id}: {current_status} → {new_status}")
    db.commit()
    db.refresh(incident)
    db.close()

    return {
        "message": "Status updated",
        "from": current_status,
        "to": new_status
    }


# RCA API (FIXED)


@app.post("/incidents/{incident_id}/rca")
def add_rca(incident_id: int, payload: RCACreate):
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

    # Prevent duplicate RCA
    if incident.rca:
        db.close()
        return {"error": "RCA already exists for this incident"}

    new_rca = RCA(
        incident_id=incident_id,
        root_cause=payload.root_cause,
        fix=payload.fix
    )

    db.add(new_rca)
    db.commit()
    print(f"[RCA ADDED] Incident {incident.id}")

    db.close()
    return {"message": "RCA added"}


# TEST ENDPOINTS


@app.get("/error")
def error():
    raise Exception("Test error")

@app.get("/slow")
def slow():
    time.sleep(1)
    return {"message": "slow response"}