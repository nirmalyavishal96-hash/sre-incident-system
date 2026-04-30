# Incident Management System (IMS)

A scalable, production-inspired Incident Management System designed to ingest high-volume signals, intelligently group them into incidents, and manage their lifecycle with mandatory Root Cause Analysis (RCA).

---

## Overview

This system simulates a real-world SRE incident platform similar to PagerDuty/Datadog.

It is designed to:

- Handle high-volume signals (burst traffic)
- Reduce alert noise via debouncing
- Track incident lifecycle
- Enforce RCA before closure
- Provide real-time dashboard visibility

---

## Architecture

    +----------------------+
    |   Signal Producer    |
    +----------+-----------+
               |
               v
    +----------------------+
    |   FastAPI Backend    |
    |  (Ingestion API)     |
    +----------+-----------+
               |
               v
    +----------------------+
    |   Redis Queue        |
    | (Backpressure Buffer)|
    +----------+-----------+
               |
               v
    +----------------------+
    |   Worker Process     |
    | (Async Processing)   |
    +----------+-----------+
               |
               v
    +----------------------+
    |   PostgreSQL DB      |
    | (Source of Truth)    |
    +----------+-----------+
               |
               v
    +----------------------+
    |   React Dashboard    |
    +----------------------+

---

## Tech Stack

| Layer | Technology | Why |
|------|------------|-----|
| Backend | FastAPI | Async support, fast development |
| Queue + Cache | Redis | Lightweight, fast, supports queueing |
| Database | PostgreSQL | Strong consistency, relational |
| Frontend | React | Simple and interactive UI |
| Containerization | Docker | Easy setup and portability |

---
## System Design Decisions

- **FastAPI** chosen for async capabilities and simplicity in building high-performance APIs.
- **Redis** used as both queue and cache to handle burst traffic and enable backpressure.
- **PostgreSQL** selected as the source of truth for strong consistency and relational modeling.
- **Worker-based architecture** ensures decoupling between ingestion and processing.
- **Debouncing via Redis TTL** reduces noise and prevents alert storms.

## Key Features

### 1. Async Signal Processing
- Signals are pushed to Redis queue
- Worker consumes asynchronously
- Prevents API overload

---

### 2. Debouncing Logic (Noise Reduction)
- Multiple signals within 10 seconds → grouped into 1 incident
- Implemented using Redis TTL

---

### 3. Incident Lifecycle (Workflow Engine)


OPEN → INVESTIGATING → RESOLVED → CLOSED


- Enforced via API
- Prevents invalid transitions

---

### 4. Mandatory RCA Validation

- Cannot close incident without RCA
- Ensures accountability

---

### 5. MTTR Calculation


MTTR = resolved_at - created_at


- Automatically calculated
- Exposed in API and UI

---

### 6. Rate Limiting

- Prevents API overload
- Basic per-IP throttling implemented

---

### 7. Observability

- `/health` endpoint
- Throughput logging (signals/sec)

---

### 8. Real-Time Dashboard

Frontend allows:

- View all incidents
- Click to view details
- Update status
- Submit RCA
- View MTTR



## Concurrency & Scaling

- Asynchronous processing implemented using Redis queue + worker model.
- System can handle burst traffic as ingestion is decoupled from processing.
- Backpressure handled via queue buffering.
- Rate limiting prevents overload at API level.

## Backpressure Handling

To handle high traffic:

- Redis queue acts as a **buffer**
- API does not directly write to DB
- Worker processes signals asynchronously


High Load → Queue absorbs → Worker processes gradually


This prevents system crashes during bursts.

---

## Data Model

### Incident
- id
- component
- status
- created_at
- resolved_at

### Signal
- id
- component
- error
- incident_id

### RCA
- incident_id
- root_cause
- fix

---

##  Setup Instructions

### 1. Clone repo

```bash
git clone https://github.com/nirmalyavishal96-hash/sre-incident-system.git
cd sre-incident-system
```
### 2. Start services
```bash
docker-compose up -d
```
### 3. Backend setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
### 4. Run worker
```bash
cd backend
python -m app.worker
```
### 5. Start frontend
```bash
cd frontend
npm install
npm start
```
## Sample Test Data

Send signals:
```bash
curl -X POST http://127.0.0.1:8000/ingest \
-H "Content-Type: application/json" \
-d '{"component":"CACHE_CLUSTER_01","error":"timeout"}'
```
## Simulating Failure Burst
```bash
for i in {1..20}; do 
  curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"component":"CACHE_CLUSTER_01","error":"timeout"}'
done
```
## Testing RCA Validation
### Should fail
```bash
PUT /incidents/{id}/status → CLOSED

# Add RCA
POST /incidents/{id}/rca

# Then close
PUT /incidents/{id}/status → CLOSED

```
## Resilience & Retry Logic

- Database writes are protected with retry mechanism.
- Worker retries operations on transient failures.
- Queue ensures signals are not lost during failures.
- RCA validation logic tested manually via API workflows



## Metrics
- Signals/sec printed every 5 seconds
- Helps monitor ingestion rate

##  Bonus Features
- Rate limiting
- MTTR calculation
- Debouncing logic
- Observability logs

## Submission Details
GitHub Repo: https://github.com/nirmalyavishal96-hash/sre-incident-system.git

Includes:

- Backend
- Frontend
- Docker setup
- README

## 🖥️ Dashboard Preview

![Dashboard](./screenshot/dashboard.png)

UI integrates fully with backend APIs and supports full incident lifecycle management
##  Development Notes

- This project was developed using iterative planning and system design prompts.
- Design decisions, architecture, and implementation steps were documented during development.
## 📁 Project Structure

backend/

app/

frontend/

screenshot/

docker-compose.yml

 README.md
# Author

Nirmalya Das