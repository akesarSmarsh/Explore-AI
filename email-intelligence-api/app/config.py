"""Application configuration settings."""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Email Intelligence API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Database paths
    sqlite_db_path: str = "./data/emails.db"
    chroma_db_path: str = "./data/chroma"
    
    # NER settings
    spacy_model: str = "en_core_web_sm"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Vector store settings
    vector_distance_metric: str = "cosine"  # Options: cosine, l2, ip
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = '["http://localhost:3000","http://localhost:5173"]'
    
    # Data settings
    sample_size: int = 10000
    
    # SMTP settings for email notifications (local mail server - Mailpit/MailHog)
    smtp_host: str = "localhost"
    smtp_port: int = 1025  # Default port for local mail servers (Mailpit, MailHog)
    smtp_user: Optional[str] = None  # Not required for local mail server
    smtp_password: Optional[str] = None  # Not required for local mail server
    smtp_from: str = "alerts@email-intelligence.local"
    smtp_use_tls: bool = False  # Disable TLS for local mail server
    smtp_use_ssl: bool = False  # Disable SSL for local mail server
    
    # Alert notification settings
    alert_recipients: str = '["admin@example.com"]'  # JSON list of recipient emails
    
    # Scheduler settings
    enable_scheduler: bool = True
    alert_check_interval_minutes: int = 5  # How often to check for alerts
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            return ["http://localhost:3000"]
    
    @property
    def alert_recipients_list(self) -> List[str]:
        """Parse alert recipients from JSON string."""
        try:
            return json.loads(self.alert_recipients)
        except json.JSONDecodeError:
            return []
    
    @property
    def smtp_configured(self) -> bool:
        """Check if SMTP is properly configured for sending emails."""
        return bool(self.smtp_host and self.smtp_from)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

