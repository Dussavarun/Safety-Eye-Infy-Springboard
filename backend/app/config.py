from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/object_detection"
    model_path: str = "/models/train7/train7/weights/best.pt"
    model_type: str = "ultralytics"
    class_map_path: str = "/app/model_data/classes.yaml"
    confidence_threshold: float = 0.25
    nms_threshold: float = 0.45

    uploads_dir: str = "/data/uploads"
    processed_dir: str = "/data/processed"


settings = Settings()
