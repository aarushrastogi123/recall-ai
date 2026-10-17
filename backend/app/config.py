from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "RECALL AI API"
    app_version: str = "0.1.0"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3221",
        "http://127.0.0.1:3221",
    ]

    # Whisper model settings
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_download_root: str | None = None

    # Upload settings
    max_upload_size: int = 100 * 1024 * 1024  # 100 MB


settings = Settings()