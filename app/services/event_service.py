"""
Event service for managing event subscriptions and broadcasting
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import aiohttp
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.models.event import Subscription, EventLog
from app.schemas.event import EventMessage, EventNotification, WebSocketConnectionInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for active WebSocket connections
active_connections: Dict[str, WebSocket] = {}
# Map of client_id to connection info
client_connections: Dict[str, WebSocketConnectionInfo] = {}
# Map of event_types to set of client_ids that are subscribed
event_subscriptions: Dict[str, Set[str]] = {}

async def connect_websocket(websocket: WebSocket, client_id: str) -> None:
    """
    Connect a WebSocket client
    """
    await websocket.accept()
    active_connections[client_id] = websocket
    
    # Initialize connection info
    if client_id not in client_connections:
        client_connections[client_id] = WebSocketConnectionInfo(
            client_id=client_id,
            subscribed_events=[],
            connected_at=datetime.utcnow()
        )
    
    logger.info(f"WebSocket client {client_id} connected")

async def disconnect_websocket(client_id: str) -> None:
    """
    Disconnect a WebSocket client
    """
    if client_id in active_connections:
        # Remove from active connections
        del active_connections[client_id]
        
        # Remove from event subscriptions
        for event_type, clients in event_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        
        # Update connection info
        if client_id in client_connections:
            del client_connections[client_id]
        
        logger.info(f"WebSocket client {client_id} disconnected")

async def subscribe_to_events(client_id: str, event_types: List[str]) -> None:
    """
    Subscribe a client to events
    """
    if client_id not in client_connections:
        logger.warning(f"Client {client_id} not found in connections")
        return
    
    for event_type in event_types:
        if event_type not in event_subscriptions:
            event_subscriptions[event_type] = set()
        
        event_subscriptions[event_type].add(client_id)
        
        # Update client's subscribed events
        if event_type not in client_connections[client_id].subscribed_events:
            client_connections[client_id].subscribed_events.append(event_type)
    
    logger.info(f"Client {client_id} subscribed to events: {event_types}")

async def unsubscribe_from_events(client_id: str, event_types: List[str]) -> None:
    """
    Unsubscribe a client from events
    """
    if client_id not in client_connections:
        logger.warning(f"Client {client_id} not found in connections")
        return
    
    for event_type in event_types:
        if event_type in event_subscriptions and client_id in event_subscriptions[event_type]:
            event_subscriptions[event_type].remove(client_id)
        
        # Update client's subscribed events
        if event_type in client_connections[client_id].subscribed_events:
            client_connections[client_id].subscribed_events.remove(event_type)
    
    logger.info(f"Client {client_id} unsubscribed from events: {event_types}")

async def broadcast_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Broadcast an event to all subscribed WebSocket clients and HTTP webhooks
    """
    # Create event message
    event_message = EventMessage(
        event_type=event_type,
        data=data,
        timestamp=datetime.utcnow()
    )
    
    # Convert to JSON
    json_data = event_message.model_dump_json()
    
    # Broadcast to WebSocket clients
    if event_type in event_subscriptions:
        subscribed_clients = event_subscriptions[event_type]
        
        for client_id in subscribed_clients:
            if client_id in active_connections:
                try:
                    await active_connections[client_id].send_text(json_data)
                    logger.debug(f"Event {event_type} sent to WebSocket client {client_id}")
                except Exception as e:
                    logger.error(f"Failed to send event to WebSocket client {client_id}: {str(e)}")
                    # Remove broken connection
                    await disconnect_websocket(client_id)
    
    # Log the event
    log_event(event_type, json_data)

def log_event(event_type: str, event_data: str) -> None:
    """
    Log an event to the database for persistence and retry
    """
    # This is a synchronized method to be called from async context
    # It should be wrapped in a thread pool executor
    from app.database.session import SessionLocal
    
    db = SessionLocal()
    try:
        event_log = EventLog(
            event_type=event_type,
            event_data=event_data,
            processed=False
        )
        db.add(event_log)
        db.commit()
        logger.debug(f"Event {event_type} logged to database")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log event to database: {str(e)}")
    finally:
        db.close()

async def process_event_queue() -> None:
    """
    Process pending events in the queue and send to HTTP webhooks
    """
    from app.database.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Get unprocessed events
        events = db.query(EventLog).filter(EventLog.processed == False).all()
        
        if not events:
            return
        
        logger.info(f"Processing {len(events)} pending events")
        
        for event in events:
            # Get subscriptions for this event type
            subscriptions = db.query(Subscription).filter(
                Subscription.event_type == event.event_type,
                Subscription.is_active == True
            ).all()
            
            if not subscriptions:
                # Mark as processed if no subscriptions
                event.processed = True
                event.processed_at = datetime.utcnow()
                continue
            
            # Parse event data
            event_data = json.loads(event.event_data)
            
            # Send to all subscribed webhooks
            for subscription in subscriptions:
                notification = EventNotification(
                    event_type=event.event_type,
                    data=event_data.get("data", {}),
                    timestamp=event_data.get("timestamp", datetime.utcnow()),
                    subscription_id=subscription.id
                )
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            subscription.callback_url,
                            json=notification.model_dump(),
                            timeout=5
                        ) as response:
                            if response.status >= 200 and response.status < 300:
                                logger.info(f"Event {event.id} sent to webhook {subscription.callback_url}")
                            else:
                                logger.warning(f"Failed to send event {event.id} to webhook {subscription.callback_url}: {response.status}")
                except Exception as e:
                    logger.error(f"Error sending event {event.id} to webhook {subscription.callback_url}: {str(e)}")
            
            # Mark as processed
            event.processed = True
            event.processed_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing event queue: {str(e)}")
    finally:
        db.close()

async def get_client_info(client_id: str) -> Optional[WebSocketConnectionInfo]:
    """
    Get WebSocket client connection info
    """
    if client_id in client_connections:
        return client_connections[client_id]
    return None

def create_subscription(db: Session, client_id: str, event_type: str, callback_url: str) -> Subscription:
    """
    Create a new HTTP webhook subscription
    """
    subscription = Subscription(
        client_id=client_id,
        event_type=event_type,
        callback_url=callback_url,
        is_active=True
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"New subscription created: {subscription}")
    
    return subscription

def update_subscription(db: Session, subscription_id: int, is_active: bool) -> Optional[Subscription]:
    """
    Update an existing subscription
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not subscription:
        return None
    
    subscription.is_active = is_active
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(subscription)
    
    logger.info(f"Subscription {subscription_id} updated: is_active={is_active}")
    
    return subscription

def delete_subscription(db: Session, subscription_id: int) -> bool:
    """
    Delete a subscription
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not subscription:
        return False
    
    db.delete(subscription)
    db.commit()
    
    logger.info(f"Subscription {subscription_id} deleted")
    
    return True

def get_subscription(db: Session, subscription_id: int) -> Optional[Subscription]:
    """
    Get a subscription by ID
    """
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()

def get_subscriptions_by_client(db: Session, client_id: str) -> List[Subscription]:
    """
    Get all subscriptions for a client
    """
    return db.query(Subscription).filter(Subscription.client_id == client_id).all()

def get_subscriptions_by_event_type(db: Session, event_type: str) -> List[Subscription]:
    """
    Get all subscriptions for an event type
    """
    return db.query(Subscription).filter(Subscription.event_type == event_type).all() 