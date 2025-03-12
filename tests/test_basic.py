"""
Basic test for the application
"""
import os
import pytest

# Set environment variables for testing
os.environ["DEBUG_MODE"] = "true"
os.environ["POSTGRES_USER"] = "postgres_test"
os.environ["POSTGRES_PASSWORD"] = "password_test"
os.environ["POSTGRES_HOST"] = "localhost_test"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "ul_transit_data_test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["UL_API_KEY"] = "test_api_key"
os.environ["DATA_COLLECTION_INTERVAL"] = "5"
os.environ["EVENT_PROCESSING_INTERVAL"] = "10"

# No need to import app or create TestClient here, it's handled in conftest.py

def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome to UL Transit Data Collector API" in response.json()["message"]

def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_api_event_types(client):
    """Test the event types endpoint"""
    response = client.get("/api/v1/events/event-types")
    assert response.status_code == 200
    assert "event_types" in response.json()
    event_types = response.json()["event_types"]
    assert any(event["name"] == "vehicle_position_update" for event in event_types)
    assert any(event["name"] == "data_collection_start" for event in event_types) 