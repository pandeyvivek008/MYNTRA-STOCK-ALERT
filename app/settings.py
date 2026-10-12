from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./stockwatch.db"
    jwt_secret: str = "development-secret-change-me-1234567890"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-before-production"
    allowed_origins: str = "*"
    integration_webhook_secret: str = "dev-webhook-secret-change-before-production"
    myntra_api_base_url: str = ""
    myntra_api_token: str = ""
    myntra_partner_store: str = ""
    myntra_warehouse_code: str = ""
    amazon_api_token: str = ""
    flipkart_api_token: str = ""
    ajio_api_token: str = ""
    nykaa_api_token: str = ""
    snapdeal_api_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_alert_to: str = ""
    whatsapp_template_name: str = "stock_alert"
    whatsapp_template_language: str = "en_US"
    whatsapp_api_version: str = "v22.0"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
