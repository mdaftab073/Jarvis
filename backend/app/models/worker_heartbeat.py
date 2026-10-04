from sqlalchemy import Column, DateTime, String

from app.db.database import Base


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id = Column(String(160), primary_key=True)
    last_heartbeat = Column(DateTime, nullable=False, index=True)
