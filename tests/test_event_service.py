"""
Tests for the event service
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.event_service import (
    active_connections,
    add_subscription,
    broadcast_event,
    broadcast_to_connection,
    log_event_to_db,
)

@pytest.mark.asyncio
async def test_add_subscription():
    """Test adding a subscription"""
    # Setup
    client_id = "test_client"
    event_type = "vehicle_position_update"
    
    # Execute
    result = await add_subscription(client_id, event_type)
    
    # Assert
    assert result["client_id"] == client_id
    assert result["event_type"] == event_type
    assert result["is_active"] is True

@pytest.mark.asyncio
async def test_broadcast_to_connection():
    """Test broadcasting to a connection"""
    # Setup
    connection = AsyncMock()
    message = {"event": "test_event", "data": "test_data"}
    
    # Execute
    await broadcast_to_connection(connection, message)
    
    # Assert
    connection.send_text.assert_called_once_with(json.dumps(message))

@pytest.mark.asyncio
async def test_broadcast_to_connection_error():
    """Test broadcasting to a connection with error"""
    # Setup
    connection = AsyncMock()
    connection.send_text.side_effect = Exception("Test exception")
    message = {"event": "test_event", "data": "test_data"}
    
    # Execute & Assert - should not raise an exception
    await broadcast_to_connection(connection, message)

@pytest.mark.asyncio
@patch("app.services.event_service.get_subscriptions_for_event_type")
async def test_broadcast_event(mock_get_subscriptions):
    """Test broadcasting an event"""
    # Setup
    event_type = "vehicle_position_update"
    event_data = {"vehicle_id": "123", "position": {"lat": 123.456, "lon": 789.012}}
    
    # Mock return value for get_subscriptions_for_event_type
    mock_subscription = MagicMock()
    mock_subscription.client_id = "test_client"
    mock_get_subscriptions.return_value = [mock_subscription]
    
    # Add a mock connection to active_connections
    connection = AsyncMock()
    active_connections["test_client"] = connection
    
    # Execute
    await broadcast_event(event_type, event_data)
    
    # Assert
    connection.send_text.assert_called_once()
    assert json.loads(connection.send_text.call_args[0][0])["event"] == event_type
    assert json.loads(connection.send_text.call_args[0][0])["data"] == event_data
    
    # Cleanup
    active_connections.pop("test_client", None)

@pytest.mark.asyncio
@patch("app.services.event_service.SessionLocal")
async def test_log_event_to_db(mock_session_local):
    """Test logging an event to the database"""
    # Setup
    event_type = "vehicle_position_update"
    event_data = {"vehicle_id": "123", "position": {"lat": 123.456, "lon": 789.012}}
    
    # Mock session
    mock_session = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_session
    
    # Execute
    await log_event_to_db(event_type, event_data)
    
    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once() 