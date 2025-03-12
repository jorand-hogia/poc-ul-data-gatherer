"""
Simple script to trigger data collection
"""
import requests
import time

API_URL = "http://localhost:8001"

def main():
    print("Triggering data collection...")
    try:
        response = requests.post(f"{API_URL}/api/v1/events/trigger-event/data_collection_start")
        print(f"Response: {response.status_code} - {response.text}")
        
        print("Checking health...")
        health_response = requests.get(f"{API_URL}/health")
        print(f"Health: {health_response.status_code} - {health_response.text}")
        
        print("Waiting 5 seconds for data collection to complete...")
        time.sleep(5)
        
        print("Checking event types...")
        event_types_response = requests.get(f"{API_URL}/api/v1/events/event-types")
        print(f"Event types: {event_types_response.status_code} - {event_types_response.text}")
        
        print("\nSuccess! The API is working correctly.")
        print("If you're not seeing WebSocket events in your client, try these troubleshooting steps:")
        print("1. Make sure your WebSocket client is connecting to the correct URL (ws://localhost:8001/api/v1/events/ws/{client_id})")
        print("2. Verify you're properly subscribing to events after connecting")
        print("3. Check browser console for any WebSocket connection errors")
        print("4. Try a different WebSocket client or library")
        print("5. Check if there's any network/firewall blocking WebSocket connections")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server. Make sure it's running on http://localhost:8001")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 