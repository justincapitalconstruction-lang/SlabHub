"""
Configuration management for SlabHub
Loads from .env and provides validated settings
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with validation"""

    # Database
    database_url: str = Field(default="sqlite:///./data/slabhub.db")

    # Application
    public_base_url: str = Field(default="http://localhost:8000")
    secret_key: str = Field(default="change-me-to-random-string-in-production")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Paths - SlabCrop Integration
    slabcrop_output_folder: str = Field(default="D:/SlabCrop/output")
    slabcrop_inbox_folder: str = Field(default="./data/slabcrop_inbox")
    incoming_raw_folder: str = Field(default="./data/incoming_raw")
    processed_archive_folder: str = Field(default="./data/archive")

    # Import Paths
    import_metadata_file: Optional[str] = Field(default=None)
    import_input_folder: Optional[str] = Field(default=None)

    # Image Processing
    image_min_width: int = Field(default=800)
    image_min_height: int = Field(default=800)
    duplicate_threshold: int = Field(default=10)
    max_image_size_mb: int = Field(default=10)

    # Label Generation
    label_size: str = Field(default="4x6")
    label_dpi: int = Field(default=203)
    label_output_folder: str = Field(default="./data/labels")

    # QR Codes
    qr_output_folder: str = Field(default="./data/qr")

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./data/logs/slabhub.log")

    # Feature Flags
    enable_auto_import: bool = Field(default=True)
    enable_watch_folder: bool = Field(default=True)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for FastAPI"""
    return settings
