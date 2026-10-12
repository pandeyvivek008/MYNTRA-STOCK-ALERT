from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./stockwatch.db"
    jwt_secret: str = "development-secret-change-me-1234567890"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-before-production"
    allowed_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
