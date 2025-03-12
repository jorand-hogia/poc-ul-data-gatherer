"""
Vehicle position model for storing transit data
"""
from datetime import datetime
from sqlalchemy import Column, Float, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class VehiclePosition(Base):
    """
    Model for storing vehicle position data from GTFS-RT feed
    """
    __tablename__ = "vehicle_positions"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String, index=True)
    route_id = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<VehiclePosition(vehicle_id='{self.vehicle_id}', route_id='{self.route_id}')>" 