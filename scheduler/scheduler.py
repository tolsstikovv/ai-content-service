import asyncio
from datetime import datetime
from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import ContentItem
from worker.tasks_generate_article import generate_article_task
from worker.tasks_generate_image import generate_image_task
from worker.tasks_publish_telegram import publish_telegram_task
from worker.tasks_publish_vk import publish_vk_task

INTERVAL_MINUTES = 60  # проверка новых задач каждый час

async def run_pipeline():
    async with async_session_factory() as session:
        # 1. Берём все draft content_items через SQLAlchemy select
        result = await session.execute(
            select(ContentItem.id).where(ContentItem.status == 'draft').order_by(ContentItem.id)
        )
        ids = result.scalars().all()

    for content_id in ids:
        try:
            # 2. Генерация статьи
            await generate_article_task(content_id)

            # 3. Генерация изображений
            await generate_image_task(content_id)

            # 4. Публикация в Telegram
            await publish_telegram_task(content_id)

            # 5. Публикация в VK
            await publish_vk_task(content_id)

        except Exception as e:
            print(f"[Pipeline] Error content_id={content_id}: {e}")


async def scheduler_loop():
    while True:
        print(f"[Scheduler] Running pipeline at {datetime.now()}")
        await run_pipeline()
        await asyncio.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(scheduler_loop())
