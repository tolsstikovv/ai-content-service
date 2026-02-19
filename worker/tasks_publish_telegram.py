import logging

from aiogram import Bot

from app.db.session import async_session_factory
from app.db.content_item_get import get_content_item_by_id
from app.db.log_error import save_error_log
from app.agents.qa_agent import analyze_article, analyze_image_generation

logger = logging.getLogger(__name__)

# TELEGRAM
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHANNEL_ID = "@your_channel_id"  # или chat_id


# =========================
# Async task
# =========================
async def publish_telegram_task(content_item_id: int) -> None:
    """
    Публикует статью + изображения в Telegram канал.
    """

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async with async_session_factory() as session:
        try:
            # 1. Получаем контент
            content_item = await get_content_item_by_id(
                session=session, content_item_id=content_item_id
            )

            if not content_item:
                await save_error_log(
                    session=session,
                    module="publish_telegram_task",
                    entity_id=content_item_id,
                    error="Content item not found",
                    severity="high",
                    cause="Invalid content_item_id",
                    recommendation="Check DB and content pipeline",
                )
                await session.commit()
                return

            if not content_item.text:
                raise RuntimeError("Article text is empty, cannot publish")

            # 2. QA проверки перед публикацией
            qa_article = await analyze_article(
                title=content_item.title,
                article_text=content_item.text,
            )

            if qa_article["score"] < 5:
                raise RuntimeError(
                    f"Article failed QA (score={qa_article['score']})"
                )

            if content_item.images:
                qa_images = await analyze_image_generation(
                    title=content_item.title,
                    images=content_item.images,
                )
                if qa_images["score"] < 5:
                    raise RuntimeError(
                        f"Images failed QA (score={qa_images['score']})"
                    )

            # 3. Публикуем текст
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=f"<b>{content_item.title}</b>\n\n{content_item.text}",
                parse_mode="HTML",
            )

            # 4. Публикуем изображения (по одному)
            if content_item.images:
                for img_url in content_item.images:
                    await bot.send_photo(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        photo=img_url,
                        caption=content_item.title,
                    )

            logger.info(
                "Content item %s published to Telegram",
                content_item_id,
            )

        except Exception as e:
            logger.exception(
                "Error publishing content_item_id=%s to Telegram",
                content_item_id,
            )

            # Логирование ошибки
            await save_error_log(
                session=session,
                module="publish_telegram_task",
                entity_id=content_item_id,
                error=str(e),
                severity="high",
                cause=None,
                recommendation="Check Telegram bot token, channel, content quality",
            )
            await session.commit()
