from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String, index=True)
    status = Column(String, default="OPEN")
    severity = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # relationship FIXED
    signals = relationship("Signal", back_populates="incident")
    rca = relationship("RCA", uselist=False, back_populates="incident")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String)
    error = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    incident_id = Column(Integer, ForeignKey("incidents.id"))

    # MUST match "signals"
    incident = relationship("Incident", back_populates="signals")


class RCA(Base):
    __tablename__ = "rca"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    root_cause = Column(Text)
    fix = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # MUST match "rca"
    incident = relationship("Incident", back_populates="rca")