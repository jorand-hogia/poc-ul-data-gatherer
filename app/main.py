"""
Main application module for UL Transit Data Collector
"""
import logging
import time
import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.database.session import engine, get_db
from app.models.vehicle import Base as VehicleBase
from app.models.event import Base as EventBase
from app.models.vehicle import VehiclePosition
from app.api import vehicle_positions, events
from app.services.gtfs_service import fetch_and_store_ul_data
from app.services.event_service import process_event_queue, broadcast_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create schedulers for data collection and event processing
data_scheduler = BackgroundScheduler()
event_scheduler = BackgroundScheduler()

# Thread pool for running async tasks in the scheduler
thread_pool = ThreadPoolExecutor(max_workers=4)

# Event to signal when API is ready
api_ready = threading.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application
    Handles startup and shutdown events
    """
    # Create database tables
    logger.info("Creating database tables...")
    VehicleBase.metadata.create_all(bind=engine)
    EventBase.metadata.create_all(bind=engine)
    
    # Start data collection scheduler
    logger.info("Starting data collection scheduler...")
    data_scheduler.add_job(
        fetch_and_store_ul_data,
        'interval',
        seconds=settings.DATA_COLLECTION_INTERVAL,
        id='ul_data_collector'
    )
    data_scheduler.start()
    
    # Start event processing scheduler
    logger.info("Starting event processing scheduler...")
    event_scheduler.add_job(
        lambda: thread_pool.submit(run_event_processor),
        'interval',
        seconds=settings.EVENT_PROCESSING_INTERVAL,
        id='event_processor'
    )
    event_scheduler.start()
    
    # Signal that the API is ready
    logger.info("API is ready!")
    api_ready.set()
    
    # Yield control to FastAPI
    yield
    
    # Shutdown schedulers
    logger.info("Shutting down schedulers...")
    data_scheduler.shutdown()
    event_scheduler.shutdown()
    thread_pool.shutdown()

def run_event_processor():
    """
    Run the event processor in a separate thread
    """
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the event processor
    loop.run_until_complete(process_event_queue())
    loop.close()

def run_initial_data_collection():
    """
    Run the initial data collection in a separate thread
    """
    logger.info("Waiting for API to be ready before starting initial data collection...")
    # Wait for API to be ready
    api_ready.wait()
    
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Broadcast the start event and run data collection
    try:
        logger.info("Running initial data collection...")
        loop.run_until_complete(
            broadcast_event(
                "data_collection_start", 
                {"timestamp": asyncio.get_event_loop().time(), "is_initial": True}
            )
        )
        # The actual collection will be triggered by the event handler
    except Exception as e:
        logger.error(f"Error in initial data collection: {str(e)}")
    finally:
        loop.close()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# Include API routers
app.include_router(
    vehicle_positions.router,
    prefix=f"{settings.API_V1_STR}/vehicle-positions",
    tags=["vehicle-positions"]
)

app.include_router(
    events.router,
    prefix=f"{settings.API_V1_STR}/events",
    tags=["events"]
)

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Welcome to UL Transit Data Collector API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    """
    # Check database connection
    try:
        # Try to get one record from the database
        db.query(VehiclePosition).limit(1).all()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check UL API connection status (without actually fetching data)
    return {
        "status": "healthy",
        "database": db_status,
        "api_ready": api_ready.is_set(),
        "schedulers": {
            "data_scheduler": data_scheduler.running,
            "event_scheduler": event_scheduler.running
        },
        "timestamp": time.time()
    }

# Run data collection once at startup in a separate thread
@app.on_event("startup")
async def startup_event():
    """
    Run data collection once at startup
    """
    # Start initial data collection in a separate thread
    thread_pool.submit(run_initial_data_collection) 