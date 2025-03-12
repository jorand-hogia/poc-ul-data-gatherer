"""
Service for handling GTFS-RT data from UL
"""
import os
import asyncio
import requests
import logging
import json
import random
from datetime import datetime
from sqlalchemy.orm import Session
from google.transit import gtfs_realtime_pb2
from dotenv import load_dotenv

from app.models.vehicle import VehiclePosition
from app.database.session import SessionLocal
from app.services import event_service

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UL API URL and key
UL_API_URL = "https://opendata.samtrafiken.se/gtfs-rt/ul/VehiclePositions.pb"
UL_API_KEY = os.getenv("UL_API_KEY", "1119e1dd46ba40ae968080127b06d53e")

# Debug mode for testing without external API
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

def fetch_ul_vehicle_positions():
    """
    Fetch vehicle positions from UL API
    
    Returns:
        list[dict]: List of vehicle position data
    """
    if DEBUG_MODE:
        logger.info("DEBUG MODE: Generating mock vehicle positions")
        return generate_mock_vehicle_positions()
        
    try:
        # Prepare URL with API key
        url = f"{UL_API_URL}?key={UL_API_KEY}"
        
        # Fetch data
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse protobuf feed
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        # Process vehicle positions
        positions = []
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                vehicle = entity.vehicle
                positions.append({
                    "vehicle_id": vehicle.vehicle.id,
                    "route_id": vehicle.trip.route_id,
                    "latitude": vehicle.position.latitude,
                    "longitude": vehicle.position.longitude,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        logger.info(f"Fetched {len(positions)} vehicle positions from UL API")
        return positions
        
    except Exception as e:
        logger.error(f"Error fetching UL vehicle positions: {str(e)}")
        return []

def generate_mock_vehicle_positions(count=10):
    """
    Generate mock vehicle positions for testing
    
    Args:
        count: Number of mock positions to generate
        
    Returns:
        list[dict]: List of mock vehicle position data
    """
    positions = []
    route_ids = ["1", "2", "3", "4", "5"]
    
    for i in range(count):
        vehicle_id = f"test-vehicle-{i+1}"
        
        positions.append({
            "vehicle_id": vehicle_id,
            "route_id": random.choice(route_ids),
            "latitude": 59.85 + random.random() * 0.1,
            "longitude": 17.72 + random.random() * 0.1,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    logger.info(f"Generated {len(positions)} mock vehicle positions")
    return positions

def store_vehicle_positions(positions: list):
    """
    Store vehicle positions in the database and broadcast events
    
    Args:
        positions: List of vehicle position dictionaries
    
    Returns:
        dict: Map of vehicle_id to stored position record
    """
    if not positions:
        logger.warning("No vehicle positions to store")
        return {}
    
    # Get a database session
    db = SessionLocal()
    
    # Track stored positions and route changes
    stored_positions = {}
    route_changes = []
    
    try:
        # Create and add database records
        for pos in positions:
            # Check for route changes
            vehicle_id = pos["vehicle_id"]
            
            # Get the latest position for this vehicle
            latest_position = db.query(VehiclePosition).filter(
                VehiclePosition.vehicle_id == vehicle_id
            ).order_by(VehiclePosition.timestamp.desc()).first()
            
            # Create new position record
            vehicle_position = VehiclePosition(
                vehicle_id=vehicle_id,
                route_id=pos["route_id"],
                latitude=pos["latitude"],
                longitude=pos["longitude"]
            )
            db.add(vehicle_position)
            
            # Check for route change
            if latest_position and latest_position.route_id != pos["route_id"]:
                route_changes.append({
                    "vehicle_id": vehicle_id,
                    "old_route_id": latest_position.route_id,
                    "new_route_id": pos["route_id"],
                    "position": pos
                })
            
            # Store in our map
            stored_positions[vehicle_id] = pos
        
        # Commit changes
        db.commit()
        logger.info(f"Stored {len(positions)} vehicle positions in the database")
        
        # Broadcast events asynchronously (will be handled outside this function)
        if route_changes:
            logger.info(f"Detected {len(route_changes)} route changes")
        
        return {
            "positions": stored_positions,
            "route_changes": route_changes
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing vehicle positions: {str(e)}")
        return {}
    
    finally:
        db.close()

async def broadcast_position_events(result):
    """
    Broadcast events for position updates and route changes
    
    Args:
        result: Dictionary containing positions and route_changes
    """
    try:
        positions = result.get("positions", {})
        route_changes = result.get("route_changes", [])
        
        # Broadcast individual position updates
        for vehicle_id, position in positions.items():
            await event_service.broadcast_event(
                "vehicle_position_update",
                {"vehicle_id": vehicle_id, "position": position}
            )
        
        # Broadcast route changes
        for change in route_changes:
            await event_service.broadcast_event(
                "vehicle_route_change",
                change
            )
        
        # Broadcast data collection complete event
        await event_service.broadcast_event(
            "data_collection_complete",
            {"timestamp": datetime.utcnow().isoformat(), "count": len(positions)}
        )
    
    except Exception as e:
        logger.error(f"Error broadcasting events: {str(e)}")

def fetch_and_store_ul_data():
    """
    Fetch vehicle positions from UL API, store in database, and broadcast events
    
    Returns:
        list: List of stored positions
    """
    positions = fetch_ul_vehicle_positions()
    result = store_vehicle_positions(positions)
    
    # Run event broadcasting in the background
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Create new event loop if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.create_task(broadcast_position_events(result))
    
    return positions 