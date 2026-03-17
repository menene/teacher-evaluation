from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_NAME: str = "teacher_analysis"
    DB_USER: str = "teacher_user"
    DB_PASSWORD: str
    DB_ROOT_PASSWORD: str = ""

    # App
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    REDIS_URL: str = "redis://redis:6379/0"

    # DeepL
    DEEPL_API_KEY: str = ""

    # LibreTranslate (self-hosted fallback)
    LIBRETRANSLATE_URL: str = "http://libretranslate:5000"

    # Derived
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
