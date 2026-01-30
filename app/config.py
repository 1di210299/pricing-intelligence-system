"""Configuration module using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI Configuration
    openai_api_key: str = ""
    
    # ScrapFly Configuration
    scrapfly_api_key: str = ""
    use_scrapfly: bool = True  # Use ScrapFly for production, Playwright for local
    
    # Database Configuration
    database_url: str = ""
    use_database: bool = False  # Set to True to use PostgreSQL instead of CSV
    
    # eBay API Configuration (deprecated)
    ebay_app_id: str = ""
    ebay_cert_id: str = ""
    ebay_dev_id: str = ""
    ebay_environment: str = "SANDBOX"
    
    # Cache Configuration
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    cache_ttl: int = 3600
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
