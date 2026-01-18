from pydantic_settings import BaseSettings
from typing import Literal, Optional
from pydantic import computed_field


class Settings(BaseSettings):
    """Application settings with environment-based configuration."""
    
    # App
    APP_NAME: str = "Appointment Tracker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Database - can use either DATABASE_URL or individual PG variables
    DATABASE_URL: Optional[str] = "postgresql://admin:admin@localhost:5432/appointment_tracker"
    PGHOST: Optional[str] = "localhost"
    PGPORT: Optional[int] = 5432
    PGUSER: Optional[str] = "admin"
    PGPASSWORD: Optional[str] = "admin"
    PGDATABASE: Optional[str] = None
    
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"  # Default for dev, should be set in .env for production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:5173"
    
    # Multi-tenant
    TENANT_HEADER: str = "X-Tenant-ID"
    
    # WhatsApp/Notification
    WHATSAPP_PROVIDER: str = "twilio"  # twilio or gupshup
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None
    GUPSHUP_API_KEY: Optional[str] = None
    GUPSHUP_APP_NAME: Optional[str] = None
    
    @computed_field
    @property
    def database_url(self) -> str:
        """Build DATABASE_URL from individual PG variables if not provided directly."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if not all([self.PGHOST, self.PGUSER, self.PGPASSWORD, self.PGDATABASE]):
            raise ValueError(
                "Either DATABASE_URL must be set, or all of PGHOST, PGUSER, PGPASSWORD, and PGDATABASE must be set"
            )
        
        return f"postgresql://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

