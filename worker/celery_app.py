import asyncio
import logging
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import ContentItem
from worker.tasks_generate_article import generate_article_task
from worker.tasks_generate_image import generate_image_task
from worker.tasks_publish_telegram import publish_telegram_task
from worker.tasks_publish_vk import publish_vk_task

logger = logging.getLogger(__name__)

# =========================
# Celery конфигурация
# =========================
celery_app = Celery(
    "content_pipeline",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


# =========================
# Async runner helper
# =========================
def run_async(task_func, *args, **kwargs):
    """
    Обёртка для запуска async функций в Celery sync context.
    """
    return asyncio.run(task_func(*args, **kwargs))


# =========================
# Celery tasks
# =========================
@celery_app.task(bind=True, name="generate_article")
def celery_generate_article(self, content_item_id: int):
    logger.info(f"[Celery] generate_article content_item_id={content_item_id}")
    return run_async(generate_article_task, content_item_id)


@celery_app.task(bind=True, name="generate_image")
def celery_generate_image(self, content_item_id: int):
    logger.info(f"[Celery] generate_image content_item_id={content_item_id}")
    return run_async(generate_image_task, content_item_id)


@celery_app.task(bind=True, name="publish_telegram")
def celery_publish_telegram(self, content_item_id: int):
    logger.info(f"[Celery] publish_telegram content_item_id={content_item_id}")
    return run_async(publish_telegram_task, content_item_id)


@celery_app.task(bind=True, name="publish_vk")
def celery_publish_vk(self, content_item_id: int):
    logger.info(f"[Celery] publish_vk content_item_id={content_item_id}")
    return run_async(publish_vk_task, content_item_id)


# =========================
# Composite pipeline task
# =========================
@celery_app.task(bind=True, name="full_pipeline")
def celery_full_pipeline(self, content_item_id: int):
    """
    Полный pipeline: generate_article -> generate_image -> publish_telegram -> publish_vk
    """
    logger.info(f"[Celery] Running full pipeline for content_item_id={content_item_id}")

    try:
        run_async(generate_article_task, content_item_id)
        run_async(generate_image_task, content_item_id)
        run_async(publish_telegram_task, content_item_id)
        run_async(publish_vk_task, content_item_id)
        logger.info(f"[Celery] Full pipeline finished for content_item_id={content_item_id}")

    except Exception as e:
        logger.exception(f"[Celery] Full pipeline failed for content_item_id={content_item_id}: {e}")
        # Правильный retry без обращения к user_options
        raise self.retry(exc=e, countdown=60, max_retries=3)
