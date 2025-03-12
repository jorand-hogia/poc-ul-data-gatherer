"""
Very simple WebSocket client for testing events
"""
import asyncio
import json
import websockets
import os
import sys
import time

# Enable debug mode for mock data
os.environ["DEBUG_MODE"] = "true"

# WebSocket URL
WS_URL = "ws://localhost:8001/api/v1/events/ws/simple-client"

async def connect_and_listen():
    """Connect to WebSocket and listen for events"""
    print(f"Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Receive welcome message
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Subscribe to events
            print("Subscribing to events...")
            await websocket.send(json.dumps({
                "action": "subscribe",
                "event_types": ["vehicle_position_update", "data_collection_start", "data_collection_complete"]
            }))
            
            # Receive subscription confirmation
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Start data collection
            print("\nNow manually trigger data collection using:")
            print("curl -X POST http://localhost:8001/api/v1/events/trigger-event/data_collection_start")
            print("\nOr try in PowerShell:")
            print("Invoke-WebRequest -Uri http://localhost:8001/api/v1/events/trigger-event/data_collection_start -Method POST")
            
            # Listen for events
            print("\nListening for events (press Ctrl+C to exit)...")
            count = 0
            while count < 50:  # Limit to 50 events to avoid overwhelming the console
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    event = json.loads(response)
                    if event.get("event_type") == "vehicle_position_update":
                        print(f"Vehicle position update for: {event['data']['vehicle_id']}")
                        count += 1
                    else:
                        print(f"Received event: {response}")
                        count += 1
                except asyncio.TimeoutError:
                    # Add a dot to show we're still waiting
                    print(".", end="", flush=True)
                    continue
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except KeyboardInterrupt:
        print("\nExiting by user request...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Windows specific setup for asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        # Run the async function
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\nExiting by user request...")
    finally:
        print("Client closed.") 