import logging
from typing import Optional, List

from app.db.session import async_session_factory
from app.db.content_item_get import get_content_item_by_id
from app.db.content_item_update import update_content_item
from app.db.log_error import save_error_log

from app.agents.image_agent import generate_images
from app.agents.qa_agent import analyze_image_generation


logger = logging.getLogger(__name__)


async def generate_image_task(content_item_id: int) -> None:
    """
    Асинхронная таска генерации изображений под статью.

    Логика:
    1. Получаем content_item
    2. Генерируем изображения
    3. QA-проверка результата
    4. Сохраняем ссылки на изображения
    5. Логируем ошибки при сбоях
    """

    async with async_session_factory() as session:
        try:
            content_item = await get_content_item_by_id(
                session=session,
                content_item_id=content_item_id,
            )

            if not content_item:
                await save_error_log(
                    session=session,
                    module="generate_image_task",
                    entity_id=content_item_id,
                    error="Content item not found",
                    severity="high",
                    cause="Invalid content_item_id",
                    recommendation="Verify content pipeline and DB records",
                )
                await session.commit()
                return

            if not content_item.text:
                raise RuntimeError("Article text is empty, cannot generate images")

            # --- Генерация изображений ---
            images: List[str] = await generate_images(
                title=content_item.title,
                article_text=content_item.text,
                style=content_item.image_style,
                count=content_item.image_count or 1,
            )

            if not images:
                raise RuntimeError("Image generation returned empty list")

            # --- QA-проверка ---
            qa_result: Optional[dict] = await analyze_image_generation(
                title=content_item.title,
                images=images,
            )

            # --- Обновление контента ---
            await update_content_item(
                session=session,
                content_item_id=content_item_id,
                images=images,
                image_status="ready",
                image_qa_score=(qa_result or {}).get("score"),
                image_qa_comment=(qa_result or {}).get("comment"),
            )

            await session.commit()

            logger.info(
                "Images generated successfully (content_item_id=%s, count=%s)",
                content_item_id,
                len(images),
            )

        except Exception as e:
            logger.exception(
                "Error while generating images (content_item_id=%s)",
                content_item_id,
            )

            # Попытка QA-анализа ошибки
            qa_error: Optional[dict] = None
            try:
                qa_error = await analyze_image_generation(
                    title="Image generation error",
                    images=[str(e)],
                )
            except Exception:
                qa_error = None

            await save_error_log(
                session=session,
                module="generate_image_task",
                entity_id=content_item_id,
                error=str(e),
                severity=(qa_error or {}).get("severity", "high"),
                cause=(qa_error or {}).get("cause"),
                recommendation=(qa_error or {}).get("recommendation"),
            )

            await session.rollback()
            await session.commit()
