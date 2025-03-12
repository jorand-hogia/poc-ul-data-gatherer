"""
Pydantic schemas for event subscriptions and WebSocket messages
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator, HttpUrl

class SubscriptionBase(BaseModel):
    """Base schema for event subscription"""
    client_id: str = Field(..., description="Unique identifier for the client")
    event_type: str = Field(..., description="Type of event to subscribe to (e.g., 'vehicle_position_update')")
    callback_url: HttpUrl = Field(..., description="URL where events will be sent to")

class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription"""
    pass

class Subscription(SubscriptionBase):
    """Schema for response with full subscription data"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration"""
        from_attributes = True

class EventMessage(BaseModel):
    """Schema for WebSocket event messages"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EventNotification(BaseModel):
    """Schema for event notifications sent to webhook subscribers"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    subscription_id: int

class WebSocketConnectionInfo(BaseModel):
    """Schema for WebSocket connection information"""
    client_id: str
    subscribed_events: List[str] = Field(default_factory=list)
    connected_at: datetime = Field(default_factory=datetime.utcnow)

class WebSocketCommand(BaseModel):
    """Schema for commands sent over WebSocket"""
    action: str = Field(..., description="Command action (subscribe, unsubscribe)")
    event_types: List[str] = Field(..., description="Event types to apply action to")

class EventLogCreate(BaseModel):
    """Schema for creating event log entries"""
    event_type: str
    event_data: str

class EventLog(EventLogCreate):
    """Schema for response with full event log data"""
    id: int
    processed: bool
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration"""
        from_attributes = True 