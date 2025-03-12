"""
Event subscription models for the event-based API
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Subscription(Base):
    """
    Model for storing event subscriptions
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    callback_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, client_id='{self.client_id}', event_type='{self.event_type}')>"

class EventLog(Base):
    """
    Model for logging events that have been triggered
    """
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)
    event_data = Column(String, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<EventLog(id={self.id}, event_type='{self.event_type}', processed={self.processed})>" 