"""Configuration centralisee de l'application, lue depuis les variables d'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de donnees
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Securite
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # Verrouillage brute-force (cahier des charges section 7)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Seed
    seed_admin_email: str = "admin@sentinel-ops.local"

    # CORS
    cors_allowed_origins: str = "https://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",")]


settings = Settings()
