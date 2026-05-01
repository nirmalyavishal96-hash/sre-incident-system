import time
import json
from app.database import SessionLocal, redis_client
from app.models import Incident, Signal

print("Worker started...")

ACTIVE_STATES = ["OPEN", "INVESTIGATING"]

while True:
    data = redis_client.lpop("signal_queue")

    if not data:
        time.sleep(1)
        continue

    data = json.loads(data)
    component = data.get("component", "unknown")
    severity = data.get("severity", "P2")

    db = SessionLocal()

    # Check for active incidents (OPEN + INVESTIGATING)
    incident = db.query(Incident).filter(
        Incident.component == component,
        Incident.status.in_(ACTIVE_STATES)
    ).first()

    if incident:
        print(f"[WORKER] Reusing incident {incident.id} for component={component}")
    else:
        incident = Incident(
          component=component,
          status="OPEN",
          severity=severity
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        print(f"[WORKER] Creating new incident for component={component}")

    signal = Signal(
        component=component,
        incident_id=incident.id
    )

    db.add(signal)
    db.commit()

    db.close()