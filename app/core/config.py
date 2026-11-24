import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
#SECRET_KEY = os.getenv("SECRET_KEY")

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    email_verification_expire_mins: int = 60 * 24
    password_reset_expire_mins: int = 30
    
model_config = SettingsConfigDict(env_file=".env")
settings = Settings()