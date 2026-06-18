"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with defaults for development."""

    # Application
    app_name: str = "Contract Manager"
    app_version: str = "0.0.2"
    base_path: str = "/projects/contract-manager-fresh"
    version_token: str = "0.0.2"

    # Database
    database_url: str = "sqlite:///./data/contract_manager.db"

    # Session
    secret_key: str = "dev-secret-change-in-production"
    session_max_age: int = 86400  # 24 hours in seconds

    # Upload
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    # Allowed attachment MIME types
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    # Demo accounts (used only for seeding)
    demo_admin_username: str = "admin"
    demo_admin_password: str = "admin123"
    demo_user_username: str = "user"
    demo_user_password: str = "user123"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
