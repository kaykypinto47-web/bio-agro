from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://bio_agro_user:change_this_local_password@localhost:5432/bio_agro"
    secret_key: str = "dev-only-change-me"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_email: str = "admin@bioagro.co.mz"
    admin_password: str = "Admin@12345"
    public_url: str = "http://localhost:5173"
    login_max_failures: int = 5
    login_window_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
