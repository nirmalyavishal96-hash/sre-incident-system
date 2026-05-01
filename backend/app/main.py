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


# PROMETHEUS METRICS (FINAL)


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

# NEW — LATENCY HISTOGRAM
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"]
)


# GLOBAL MIDDLEWARE (COUNT + LATENCY)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        # Capture errors
        status_code = 500
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status_code
        ).inc()

        # Also track latency
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(latency)

        raise  # re-raise error

    # Normal request
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


# Metrics Logging (Signals/sec)


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
RATE_LIMIT = 5
WINDOW = 10


# Root


@app.get("/")
def root():
    return {"message": "IMS Backend Running"}


# Health


@app.get("/health")
def health():
    return {"status": "ok"}


# Prometheus Metrics Endpoint


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Ingestion API


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

    # Push to Redis
    redis_client.rpush("signal_queue", json.dumps(payload))

    # Update queue metric
    QUEUE_SIZE.set(redis_client.llen("signal_queue"))

    signal_count += 1

    return {"status": "queued"}


# Get Incidents (MTTR)


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


# Update Status


@app.put("/incidents/{incident_id}/status")
def update_status(incident_id: int, payload: StatusUpdate):
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        db.close()
        return {"error": "Incident not found"}

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
@app.get("/error")
def error():
    raise Exception("Test error")

import time

@app.get("/slow")
def slow():
    time.sleep(1)  # simulate slow API
    return {"message": "slow response"}