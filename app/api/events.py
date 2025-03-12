"""
API endpoints for event subscriptions and WebSocket connections
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.event import Subscription, EventLog
from app.schemas.event import (
    Subscription as SubscriptionSchema,
    SubscriptionCreate,
    WebSocketCommand,
    EventMessage,
    EventLog as EventLogSchema,
)
from app.services import event_service

router = APIRouter()

# HTTP REST Endpoints for subscription management
@router.post("/subscriptions", response_model=SubscriptionSchema)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new event subscription
    """
    try:
        return event_service.create_subscription(
            db=db,
            client_id=subscription.client_id,
            event_type=subscription.event_type,
            callback_url=str(subscription.callback_url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create subscription: {str(e)}")

@router.get("/subscriptions", response_model=List[SubscriptionSchema])
async def get_subscriptions(
    client_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get subscriptions, optionally filtered by client_id or event_type
    """
    if client_id:
        return event_service.get_subscriptions_by_client(db, client_id)
    elif event_type:
        return event_service.get_subscriptions_by_event_type(db, event_type)
    else:
        # Get all subscriptions
        return db.query(Subscription).all()

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionSchema)
async def get_subscription(
    subscription_id: int = Path(...),
    db: Session = Depends(get_db)
):
    """
    Get a subscription by ID
    """
    subscription = event_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return subscription

@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionSchema)
async def update_subscription(
    subscription_id: int = Path(...),
    is_active: bool = Query(...),
    db: Session = Depends(get_db)
):
    """
    Update a subscription's active status
    """
    subscription = event_service.update_subscription(db, subscription_id, is_active)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return subscription

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int = Path(...),
    db: Session = Depends(get_db)
):
    """
    Delete a subscription
    """
    result = event_service.delete_subscription(db, subscription_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return {"status": "success", "message": f"Subscription {subscription_id} deleted"}

@router.get("/event-types")
async def get_event_types():
    """
    Get all available event types
    """
    return {
        "event_types": [
            {
                "name": "vehicle_position_update",
                "description": "Triggered when a vehicle position is updated"
            },
            {
                "name": "vehicle_route_change",
                "description": "Triggered when a vehicle changes its route"
            },
            {
                "name": "data_collection_complete", 
                "description": "Triggered when a data collection cycle is complete"
            },
            {
                "name": "data_collection_start",
                "description": "Triggered to start a new data collection cycle"
            }
        ]
    }

@router.get("/events", response_model=List[EventLogSchema])
async def get_events(
    event_type: Optional[str] = Query(None),
    processed: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get event logs, optionally filtered by event_type or processed status
    """
    query = db.query(EventLog)
    
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    
    if processed is not None:
        query = query.filter(EventLog.processed == processed)
    
    return query.order_by(EventLog.created_at.desc()).limit(limit).all()

@router.get("/event-history/{event_type}", response_model=List[EventLogSchema])
async def get_event_history(
    event_type: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get historical events of a specific type
    
    This endpoint allows retrieving past events filtered by type and time range.
    """
    query = db.query(EventLog).filter(EventLog.event_type == event_type)
    
    if start_time:
        query = query.filter(EventLog.created_at >= start_time)
    if end_time:
        query = query.filter(EventLog.created_at <= end_time)
        
    return query.order_by(EventLog.created_at.desc()).limit(limit).all()

# WebSocket endpoint for real-time events
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time event notifications
    """
    # Generate a unique client ID if not provided
    if not client_id or client_id == "generate":
        client_id = f"ws-{uuid.uuid4()}"
    
    # Connect the client
    await event_service.connect_websocket(websocket, client_id)
    
    try:
        # Send welcome message with client ID
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "message": "Connected to event stream"
        })
        
        # Listen for commands from the client
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            
            try:
                # Parse the command
                command = WebSocketCommand.model_validate_json(data)
                
                # Process command
                if command.action == "subscribe":
                    await event_service.subscribe_to_events(client_id, command.event_types)
                    await websocket.send_json({
                        "type": "subscription_update",
                        "status": "subscribed",
                        "event_types": command.event_types
                    })
                elif command.action == "unsubscribe":
                    await event_service.unsubscribe_from_events(client_id, command.event_types)
                    await websocket.send_json({
                        "type": "subscription_update",
                        "status": "unsubscribed",
                        "event_types": command.event_types
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {command.action}"
                    })
            except Exception as e:
                # Send error message for invalid commands
                await websocket.send_json({
                    "type": "error",
                    "message": f"Invalid command: {str(e)}"
                })
    except WebSocketDisconnect:
        # Client disconnected
        await event_service.disconnect_websocket(client_id)
    except Exception as e:
        # Handle other exceptions
        await event_service.disconnect_websocket(client_id)
        raise

# Helper endpoint to manually trigger an event (for testing)
@router.post("/trigger-event/{event_type}")
async def trigger_event(
    event_type: str = Path(...),
    data: Dict[str, Any] = None
):
    """
    Manually trigger an event (for testing purposes)
    """
    if data is None:
        data = {"message": "Test event", "timestamp": str(asyncio.get_event_loop().time())}
    
    # Special handling for data_collection_start
    if event_type == "data_collection_start":
        from app.services.gtfs_service import fetch_and_store_ul_data
        # Run data collection in background
        asyncio.create_task(handle_data_collection())
        return {"status": "success", "message": "Data collection started"}
    
    # Broadcast the event
    await event_service.broadcast_event(event_type, data)
    
    return {"status": "success", "message": f"Event {event_type} triggered", "data": data}

async def handle_data_collection():
    """
    Handle data collection and broadcast events
    """
    from app.services.gtfs_service import fetch_and_store_ul_data
    
    # Broadcast start event
    await event_service.broadcast_event("data_collection_start", {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "started"
    })
    
    try:
        # Run data collection
        result = fetch_and_store_ul_data()
        
        # Broadcast completion event
        await event_service.broadcast_event("data_collection_complete", {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "count": len(result) if result else 0
        })
    except Exception as e:
        # Broadcast error event
        await event_service.broadcast_event("data_collection_error", {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }) 