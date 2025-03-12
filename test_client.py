"""
Test client for UL Transit Data Collector API
"""
import asyncio
import json
import sys
import time
import logging
import websockets
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_client")

# API URL
API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/api/v1/events/ws/test-client"

async def test_websocket():
    """Test WebSocket connection and event subscription"""
    logger.info(f"Connecting to WebSocket at {WS_URL}")
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Receive welcome message
            response = await websocket.recv()
            logger.info(f"Received welcome message: {response}")
            
            # Subscribe to events
            subscription = {
                "action": "subscribe",
                "event_types": ["vehicle_position_update", "vehicle_route_change", "data_collection_start", "data_collection_complete"]
            }
            logger.info(f"Subscribing to events: {subscription}")
            await websocket.send(json.dumps(subscription))
            
            # Receive subscription confirmation
            response = await websocket.recv()
            logger.info(f"Received subscription response: {response}")
            
            # Trigger data collection
            logger.info("Triggering data collection...")
            requests.post(f"{API_URL}/api/v1/events/trigger-event/data_collection_start")
            
            # Listen for events
            logger.info("Waiting for events...")
            for _ in range(10):  # Listen for 10 events max
                response = await websocket.recv()
                event = json.loads(response)
                logger.info(f"Received event: {json.dumps(event, indent=2)}")
                
                # If we received a data_collection_complete event, we can stop
                if isinstance(event, dict) and event.get("event_type") == "data_collection_complete":
                    logger.info("Data collection completed, exiting...")
                    break
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket test: {e}")

def test_rest_api():
    """Test REST API endpoints"""
    logger.info(f"Testing REST API at {API_URL}")
    
    try:
        # Test health endpoint
        logger.info("Checking health endpoint...")
        response = requests.get(f"{API_URL}/health")
        logger.info(f"Health response: {json.dumps(response.json(), indent=2)}")
        
        # Test event types endpoint
        logger.info("Checking event types...")
        response = requests.get(f"{API_URL}/api/v1/events/event-types")
        logger.info(f"Event types: {json.dumps(response.json(), indent=2)}")
        
        # Test getting latest vehicle positions
        logger.info("Getting latest vehicle positions...")
        response = requests.get(f"{API_URL}/api/v1/vehicle-positions/latest")
        if response.status_code == 200:
            positions = response.json()
            logger.info(f"Found {len(positions)} vehicle positions")
            
            if positions:
                # Show first position as example
                logger.info(f"Example position: {json.dumps(positions[0], indent=2)}")
        else:
            logger.error(f"Error getting vehicle positions: {response.status_code} - {response.text}")
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Error in REST API test: {e}")

async def main():
    """Run the test client"""
    logger.info("Starting test client")
    
    # Test REST API first
    test_rest_api()
    
    # Then test WebSocket
    await test_websocket()
    
    logger.info("Test client completed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 