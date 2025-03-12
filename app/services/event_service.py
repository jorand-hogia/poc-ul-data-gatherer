"""
Event service for managing WebSocket connections and subscriptions.
Handles broadcasting events to subscribers and logging events to the database.
"""
# Remove unused import
# import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import WebSocket
# Remove unused import
# from fastapi import WebSocketDisconnect

from app.models.event import EventLog, Subscription
from app.schemas.event import EventCreate

# In-memory storage for WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# In-memory storage for event history
event_history: Dict[str, List[Dict[str, Any]]] = {}

# Maximum number of events to keep in history per event type
MAX_HISTORY_EVENTS = 100

async def add_connection(client_id: str, websocket: WebSocket) -> None:
    """
    Store a WebSocket connection for a client.
    
    Args:
        client_id: Unique identifier for the client
        websocket: WebSocket connection
    """
    active_connections[client_id] = websocket

async def remove_connection(client_id: str) -> None:
    """
    Remove a WebSocket connection for a client.
    
    Args:
        client_id: Unique identifier for the client
    """
    if client_id in active_connections:
        del active_connections[client_id]

async def add_subscription(client_id: str, event_type: str) -> Dict[str, Any]:
    """
    Add a subscription for a client to receive events of a specific type.
    
    Args:
        client_id: Unique identifier for the client
        event_type: Type of event to subscribe to
        
    Returns:
        Subscription information
    """
    subscription = {
        "client_id": client_id,
        "event_type": event_type,
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
    
    # Log subscription
    logging.info("Added subscription: %s", subscription)
    
    return subscription

async def remove_subscription(client_id: str, event_type: str) -> Dict[str, Any]:
    """
    Remove a subscription for a client.
    
    Args:
        client_id: Unique identifier for the client
        event_type: Type of event to unsubscribe from
        
    Returns:
        Subscription information with is_active set to False
    """
    subscription = {
        "client_id": client_id,
        "event_type": event_type,
        "is_active": False,
        "removed_at": datetime.now().isoformat()
    }
    
    # Log unsubscription
    logging.info("Removed subscription: %s", subscription)
    
    return subscription

async def broadcast_to_connection(connection: WebSocket, message: Dict[str, Any]) -> None:
    """
    Send a message to a specific WebSocket connection.
    
    Args:
        connection: WebSocket connection
        message: Message to send
    """
    try:
        # Convert message to JSON string
        json_message = json.dumps(message)
        logging.info("Broadcasting message: %s", json_message)
        await connection.send_text(json_message)
    except Exception as e:
        logging.error("Error broadcasting message: %s", str(e))

async def log_event_to_db(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Log an event to the database.
    
    Args:
        event_type: Type of event
        event_data: Event data
    """
    # Import inside function to avoid circular import
    from app.database.session import SessionLocal
    
    event_create = EventCreate(
        event_type=event_type,
        data=event_data,
        created_at=datetime.now()
    )
    
    try:
        # Create event log entry
        with SessionLocal() as db:
            event_log = EventLog(
                event_type=event_create.event_type,
                data=event_create.data,
                created_at=event_create.created_at,
                processed=False
            )
            db.add(event_log)
            db.commit()
            logging.info("Logged event to database: %s", event_create.dict())
    except Exception as ex:
        logging.error("Error logging event to database: %s", str(ex))

async def add_to_history(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Add an event to the in-memory history.
    
    Args:
        event_type: Type of event
        event_data: Event data
    """
    if event_type not in event_history:
        event_history[event_type] = []
    
    # Add event to history with timestamp
    event_with_timestamp = {
        "data": event_data,
        "timestamp": datetime.now().isoformat()
    }
    event_history[event_type].append(event_with_timestamp)
    
    # Limit history size
    if len(event_history[event_type]) > MAX_HISTORY_EVENTS:
        event_history[event_type] = event_history[event_type][-MAX_HISTORY_EVENTS:]

async def process_event_queue() -> None:
    """
    Process events from the database queue.
    Broadcasts events to subscribers and marks them as processed.
    """
    # Import inside function to avoid circular import
    from app.database.session import SessionLocal
    
    try:
        with SessionLocal() as db:
            # Get unprocessed events
            unprocessed_events = db.query(EventLog).filter(EventLog.processed is False).order_by(EventLog.created_at).all()
            
            if unprocessed_events:
                logging.info("Processing %s unprocessed events", len(unprocessed_events))
                
                for event in unprocessed_events:
                    # Get subscriptions for this event type
                    subscriptions = db.query(Subscription).filter(
                        Subscription.event_type == event.event_type,
                        Subscription.is_active is True
                    ).all()
                    
                    # Broadcast to subscribers
                    for subscription in subscriptions:
                        if subscription.client_id in active_connections:
                            conn = active_connections[subscription.client_id]
                            message = {
                                "event": event.event_type,
                                "data": event.data,
                                "timestamp": event.created_at.isoformat()
                            }
                            try:
                                logging.info("Broadcasting event to client %s: %s", 
                                            subscription.client_id, message)
                                await broadcast_to_connection(conn, message)
                            except Exception as e:
                                logging.error("Error broadcasting to client %s: %s", 
                                            subscription.client_id, str(e))
                    
                    # Mark as processed
                    event.processed = True
                    db.commit()
            
            else:
                logging.info("No unprocessed events found")
                
    except Exception as ex:
        logging.error("Error processing event queue: %s", str(ex))

async def get_subscriptions_for_event_type(event_type: str) -> List[Subscription]:
    """
    Get all active subscriptions for a specific event type.
    
    Args:
        event_type: Type of event
        
    Returns:
        List of subscriptions
    """
    # Import inside function to avoid circular import
    from app.database.session import SessionLocal
    
    with SessionLocal() as db:
        return db.query(Subscription).filter(
            Subscription.event_type == event_type,
            Subscription.is_active is True
        ).all()

async def broadcast_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Broadcast an event to all subscribers.
    
    Args:
        event_type: Type of event
        event_data: Event data
    """
    # Log to database
    await log_event_to_db(event_type, event_data)
    
    # Add to in-memory history
    await add_to_history(event_type, event_data)
    
    # Get subscriptions
    subscriptions = await get_subscriptions_for_event_type(event_type)
    
    # Broadcast to subscribers
    for subscription in subscriptions:
        if subscription.client_id in active_connections:
            conn = active_connections[subscription.client_id]
            message = {
                "event": event_type,
                "data": event_data,
                "timestamp": datetime.now().isoformat()
            }
            try:
                logging.info("Broadcasting event to client %s", subscription.client_id)
                await broadcast_to_connection(conn, message)
            except Exception as e:
                logging.error("Error broadcasting to client %s: %s", 
                             subscription.client_id, str(e))

def get_event_history(event_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get event history from in-memory storage.
    
    Args:
        event_type: Type of event to get history for, or None for all event types
        
    Returns:
        Event history
    """
    if event_type:
        return {event_type: event_history.get(event_type, [])}
    else:
        return event_history 