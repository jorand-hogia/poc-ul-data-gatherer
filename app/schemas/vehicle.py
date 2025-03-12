"""
Pydantic schemas for vehicle position data
"""
from datetime import datetime
from pydantic import BaseModel, Field

class VehiclePositionBase(BaseModel):
    """Base schema for vehicle position data"""
    vehicle_id: str = Field(..., description="Unique identifier for the vehicle")
    route_id: str = Field(..., description="ID of the route the vehicle is serving")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")

class VehiclePositionCreate(VehiclePositionBase):
    """Schema for creating a new vehicle position record"""
    pass

class VehiclePosition(VehiclePositionBase):
    """Schema for response with full vehicle position data"""
    id: int
    timestamp: datetime

    class Config:
        """Pydantic configuration"""
        from_attributes = True 