import time
import json
from app.database import SessionLocal, redis_client
from app.models import Incident, Signal

print("Worker started...")

while True:
    data = redis_client.lpop("signal_queue")

    if not data:
        time.sleep(1)
        continue

    data = json.loads(data)
    component = data.get("component", "unknown")
    status = data.get("status", "unknown")

    db = SessionLocal()

    # Check for open incident
    incident = db.query(Incident).filter(
        Incident.component == component,
        Incident.status == "OPEN"
    ).first()

    if incident:
        print(f"Reusing incident {incident.id} for {component}")
    else:
        incident = Incident(component=component, status="OPEN")
        db.add(incident)
        db.commit()
        db.refresh(incident)
        print(f"Creating new incident for {component}")

    signal = Signal(component=component, incident_id=incident.id)
    db.add(signal)
    db.commit()

    db.close()