from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_BASE_URL: str = "https://django-m.chbk.app"
    API_TIMEOUT: int = 30
    
    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8080
    
    # Database
    DATABASE_URL: str = "sqlite:///./test_results.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Test Configuration
    TEST_INTERVAL_MINUTES: int = 5
    MAX_CONCURRENT_TESTS: int = 10
    
    # Audio Test Files
    TEST_AUDIO_DIR: str = "./test_audio"
    
    # Monitoring
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Alerts
    ALERT_RESPONSE_TIME_MS: int = 1000  # Alert if response time > 1s
    ALERT_ERROR_RATE_PERCENT: float = 5.0  # Alert if error rate > 5%
    
    # Authentication (if needed)
    API_TOKEN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()