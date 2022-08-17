from pydantic import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "test_project"
    ENV: str = "local"

    MONGODB_CONNECTION_URL: str

    RUN_TESTCONTAINERS: bool = False
    STOP_TESTCONTAINERS: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
