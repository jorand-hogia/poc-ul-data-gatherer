"""
Basic test for the application
"""
import os
import pytest
from fastapi.testclient import TestClient

# Set environment variables for testing
os.environ["DEBUG_MODE"] = "true"
os.environ["POSTGRES_USER"] = "postgres_test"
os.environ["POSTGRES_PASSWORD"] = "password_test"
os.environ["POSTGRES_HOST"] = "localhost_test"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "ul_transit_data_test"
os.environ["DATABASE_URL"] = "postgresql://postgres_test:password_test@localhost_test:5432/ul_transit_data_test"
os.environ["UL_API_KEY"] = "test_api_key"
os.environ["DATA_COLLECTION_INTERVAL"] = "5"
os.environ["EVENT_PROCESSING_INTERVAL"] = "10"

# Import app after setting environment variables
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome to UL Transit Data Collector API" in response.json()["message"]

def test_health_endpoint():
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_api_event_types():
    """Test the event types endpoint"""
    response = client.get("/api/v1/events/event-types")
    assert response.status_code == 200
    assert "event_types" in response.json()
    event_types = response.json()["event_types"]
    assert any(event["name"] == "vehicle_position_update" for event in event_types)
    assert any(event["name"] == "data_collection_start" for event in event_types) 