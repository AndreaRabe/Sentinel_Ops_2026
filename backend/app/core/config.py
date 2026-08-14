"""Configuration centralisee de l'application, lue depuis les variables d'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de donnees
    database_url: str

    # Securite
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # Cookie de refresh token : Secure desactive par defaut (dev en HTTP simple).
    # A forcer a true en production, ou le trafic passe par nginx en HTTPS.
    cookie_secure: bool = False

    # Verrouillage brute-force du login (cahier des charges section 7).
    # Implemente sur une fenetre glissante lue dans audit_logs : pas de Redis,
    # qui n'est pas utilise dans ce projet.
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Documentation OpenAPI interactive. A passer a false des que l'application
    # est exposee au-dela du poste de developpement : /docs decrit la totalite
    # de la surface d'API, y compris les routes d'administration.
    docs_enabled: bool = True

    # Seed
    seed_admin_email: str = "admin@sentinel-ops.local"

    # Pieces jointes : repertoire local, hors du depot. A sauvegarder au meme
    # titre que la base (les metadonnees en DB sans les fichiers ne valent rien).
    attachments_dir: str = "storage/attachments"

    # Planification (APScheduler) - fuseau utilise pour les jobs quotidiens.
    scheduler_timezone: str = "Europe/Paris"
    scheduler_enabled: bool = True

    # CORS
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",")]


settings = Settings()
