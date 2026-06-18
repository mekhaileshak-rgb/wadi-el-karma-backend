from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Wadi El Karma"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:@localhost:3306/wadi_el_karma"

    # Security
   # بدلاً من الكود اللي بيولد توكن كل مرة:
# SECRET_KEY: str = secrets.token_urlsafe(32) 

# اكتب حاجة ثابتة زي كدة:
    SECRET_KEY: str = "my_super_secret_key_which_should_be_very_long_and_hard_to_guess"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10000
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Admin
    FIRST_ADMIN_EMAIL: str = "admin@wadielkarma.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@123456"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
