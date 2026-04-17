from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://cia:cia@localhost:5432/cia"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    openrouter_api_key: str = ""
    openrouter_model: str = "auto"
    openrouter_fallback_model: str = "qwen/qwen3-vl-32b-instruct"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001"
    )
    # PDF exports: Chromium (Playwright) matches the HTML report; set false to use xhtml2pdf only.
    report_pdf_chromium: bool = True


settings = Settings()
