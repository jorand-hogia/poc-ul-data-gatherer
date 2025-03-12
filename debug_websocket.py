"""
Debug script for WebSocket testing with verbose output
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
import websockets
import requests
from datetime import datetime

# Configure very verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug_websocket")

# API URL
API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/api/v1/events/ws/debug-client"

# Enable debug mode in environment
os.environ["DEBUG_MODE"] = "true"

async def test_websocket_connection():
    """Test basic WebSocket connection"""
    logger.info(f"Connecting to WebSocket at {WS_URL}")
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Receive welcome message
            response = await websocket.recv()
            logger.info(f"Received welcome message: {response}")
            
            # Subscribe to all events
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
            trigger_response = requests.post(f"{API_URL}/api/v1/events/trigger-event/data_collection_start")
            logger.info(f"Trigger response: {trigger_response.status_code} - {trigger_response.text}")
            
            # Listen for events
            logger.info("Waiting for events...")
            for i in range(30):  # Listen for 30 seconds max
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    event = json.loads(response)
                    logger.info(f"Received event: {json.dumps(event, indent=2)}")
                except asyncio.TimeoutError:
                    logger.debug(f"No event received for 1 second (wait {i+1}/30)")
                    # After 5 seconds with no events, trigger data collection again
                    if i == 5:
                        logger.info("No events after 5 seconds, triggering data collection again...")
                        trigger_response = requests.post(f"{API_URL}/api/v1/events/trigger-event/data_collection_start")
                        logger.info(f"Trigger response: {trigger_response.status_code} - {trigger_response.text}")
                    continue
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket test: {e}")

def check_event_subscriptions():
    """Make a direct request to check if our WebSocket client is registered"""
    try:
        logger.info("Checking API health...")
        response = requests.get(f"{API_URL}/health")
        logger.info(f"Health response: {response.status_code} - {response.text}")
        
        logger.info("Checking event types...")
        response = requests.get(f"{API_URL}/api/v1/events/event-types")
        logger.info(f"Event types: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Error checking API: {e}")

async def main():
    """Run the debug tests"""
    logger.info("Starting WebSocket debug tests")
    
    # Check API endpoints
    check_event_subscriptions()
    
    # Test WebSocket connection
    await test_websocket_connection()
    
    logger.info("Debug tests completed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 