"""
Script to run the UL Transit Data Collector application
"""
import os
import signal
import subprocess
import sys
import time
import threading
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")

def run_api_server():
    """Run the FastAPI application"""
    import uvicorn
    logger.info("Starting API server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)

def wait_for_api_server():
    """Wait for the API server to become available"""
    max_retries = 30
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get("http://localhost:8001/health")
            if response.status_code == 200:
                logger.info("API server is up and running!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        
        retries += 1
        time.sleep(1)
        logger.info(f"Waiting for API server to start... ({retries}/{max_retries})")
    
    logger.error("Failed to connect to API server after multiple attempts")
    return False

def trigger_data_collection():
    """Manually trigger a data collection cycle"""
    try:
        response = requests.post("http://localhost:8001/api/v1/events/trigger-event/data_collection_start")
        if response.status_code == 200:
            logger.info("Data collection triggered successfully")
            return True
        else:
            logger.error(f"Failed to trigger data collection: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to API server to trigger data collection")
        return False

def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    logger.info("Received shutdown signal, exiting...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Start the API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Wait for the API server to become available
    if not wait_for_api_server():
        logger.error("Failed to start API server, exiting...")
        sys.exit(1)
    
    # Trigger initial data collection
    logger.info("API server is ready, triggering initial data collection...")
    trigger_data_collection()
    
    # Keep the main thread running
    logger.info("All systems running! Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0) 