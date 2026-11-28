from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "quWP7U2nZOsyXc4qBCHoYLY2a33TM0K6DoCXKcqaPDE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "BiletFlow"
    environment: str = "development" 

    DATABASE_URL: str = "postgresql+psycopg2://biletflow:biletflow@localhost:5432/biletflow_test"

    SECRET_KEY: str = DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_mins: int = 60 * 24
    email_verification_expire_mins: int = 60 * 24
    password_reset_expire_mins: int = 30

    frontend_url: str = "http://localhost:5173"   
    api_public_url: str = "http://localhost:8000"  
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    email_backend: str = "console"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False
    email_from: str = "BiletFlow <no-reply@biletflow.local>"

    currency: str = "KZT"
    default_timezone: str = "Asia/Almaty"
    order_hold_minutes: int = 10           
    activation_fee_kzt: int = 5000          
    processing_fee_percent: float = 3.0     
    media_dir: str = "media"               
    max_upload_mb: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

if settings.environment == "production" and settings.SECRET_KEY == DEFAULT_SECRET:
    raise RuntimeError("SECRET_KEY must be set to a private random value in production")
