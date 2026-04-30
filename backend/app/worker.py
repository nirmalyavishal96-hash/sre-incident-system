from app.database import SessionLocal
from app.models import Incident, Signal
from datetime import datetime

import time
import json
from datetime import datetime, timedelta

from app.database import redis_client, SessionLocal


print("Worker started...")

DEBOUNCE_WINDOW = 10  # seconds

while True:
    data = redis_client.lpop("signal_queue")

    if data:
        signal = json.loads(data)
        component = signal.get("component")
        error = signal.get("error")

        db = SessionLocal()

        # Check Redis for existing incident
        incident_key = f"incident:{component}"
        incident_id = redis_client.get(incident_key)

        if incident_id:
            print(f"Reusing incident {incident_id} for {component}")
            incident = db.query(Incident).filter(Incident.id == int(incident_id)).first()
        else:
            print(f"Creating new incident for {component}")

            incident = Incident(
                component=component,
                status="OPEN",
                severity="P2"
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # store in Redis with expiry (debounce window)
            redis_client.setex(incident_key, DEBOUNCE_WINDOW, incident.id)

        # Store signal
        new_signal = Signal(
            component=component,
            error=error,
            incident_id=incident.id
        )

        db.add(new_signal)
        db.commit()

        db.close()

    time.sleep(1)