"""
API endpoints for vehicle position data
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.vehicle import VehiclePosition
from app.schemas.vehicle import VehiclePosition as VehiclePositionSchema

router = APIRouter()

@router.get("/", response_model=List[VehiclePositionSchema])
async def get_vehicle_positions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of vehicle positions
    """
    positions = db.query(VehiclePosition).order_by(
        VehiclePosition.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    return positions

@router.get("/latest", response_model=List[VehiclePositionSchema])
async def get_latest_vehicle_positions(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve the latest vehicle positions
    """
    # Get the latest position for each vehicle
    # This query gets the latest position for each unique vehicle_id
    latest_positions = db.query(VehiclePosition).order_by(
        VehiclePosition.vehicle_id,
        VehiclePosition.timestamp.desc()
    ).limit(limit).all()
    
    return latest_positions

@router.get("/by-route/{route_id}", response_model=List[VehiclePositionSchema])
async def get_vehicle_positions_by_route(
    route_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve vehicle positions for a specific route
    """
    positions = db.query(VehiclePosition).filter(
        VehiclePosition.route_id == route_id
    ).order_by(
        VehiclePosition.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    if not positions:
        raise HTTPException(status_code=404, detail=f"No positions found for route {route_id}")
    
    return positions

@router.get("/by-vehicle/{vehicle_id}", response_model=List[VehiclePositionSchema])
async def get_vehicle_positions_by_vehicle(
    vehicle_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve positions for a specific vehicle
    """
    positions = db.query(VehiclePosition).filter(
        VehiclePosition.vehicle_id == vehicle_id
    ).order_by(
        VehiclePosition.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    if not positions:
        raise HTTPException(status_code=404, detail=f"No positions found for vehicle {vehicle_id}")
    
    return positions 