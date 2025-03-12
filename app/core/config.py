"""
Application configuration settings
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # API Details
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "UL Transit Data Collector"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost/ul_transit_data"
    )
    
    # UL API
    UL_API_KEY: str = os.getenv("UL_API_KEY", "1119e1dd46ba40ae968080127b06d53e")
    UL_API_URL: str = "https://opendata.samtrafiken.se/gtfs-rt/ul/VehiclePositions.pb"
    
    # Data collection
    DATA_COLLECTION_INTERVAL: int = int(os.getenv("DATA_COLLECTION_INTERVAL", "1"))  # in seconds
    
    # Event processing
    EVENT_PROCESSING_INTERVAL: int = int(os.getenv("EVENT_PROCESSING_INTERVAL", "5"))  # in seconds
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # WebSocket
    WEBSOCKET_HEARTBEAT_INTERVAL: int = int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30"))  # in seconds
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }


# Create settings instance
settings = Settings() 