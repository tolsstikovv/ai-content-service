from pydantic import BaseSettings, Field
from typing import List

class Settings(BaseSettings):
    # =========================
    # Telegram
    # =========================
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = Field(..., description="Список ID админов через запятую")
    TELEGRAM_CHANNEL_ID: str

    # =========================
    # VK
    # =========================
    VK_ACCESS_TOKEN: str
    VK_GROUP_ID: int

    # =========================
    # OpenAI / AI генерация
    # =========================
    OPENAI_API_KEY: str
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"
    OPENAI_QA_MODEL: str = "gpt-4o-mini"

    # =========================
    # QA агент
    # =========================
    QA_PROVIDER: str = "openai"       # openai | stub
    QA_TIMEOUT: int = 90              # секунда

    # =========================
    # Генерация изображений
    # =========================
    IMAGE_PROVIDER: str = "openai"    # openai | stub
    IMAGE_SIZE: str = "1024x1024"
    IMAGE_QUALITY: str = "standard"

    # =========================
    # Celery / Worker / Redis
    # =========================
    REDIS_URL: str
    REDIS_BACKEND: str

    # =========================
    # Scheduler
    # =========================
    SCHEDULER_INTERVAL_MINUTES: int = 60

    # =========================
    # Общие настройки
    # =========================
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Europe/Moscow"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаём объект конфигурации
settings = Settings()
