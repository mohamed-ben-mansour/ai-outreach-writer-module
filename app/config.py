from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Agentic Outreach API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Google Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 2048
    
    # Research Tools
    USE_MOCK_DATA: bool = True
    LINKEDIN_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    CRM_DATABASE_URL: Optional[str] = None
    
    # Validation
    MIN_QUALITY_SCORE: int = 80
    MAX_ITERATIONS: int = 3
    
    # Features
    ENABLE_HUMAN_REVIEW: bool = False
    ENABLE_AUTO_SEND: bool = False
    ENABLE_LEARNING_LOOP: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()