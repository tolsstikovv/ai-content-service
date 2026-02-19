import logging
from typing import Optional


from app.db.session import async_session_factory
from app.db.content_item_get import get_content_item_by_id
from app.db.content_item_update import update_content_item
from app.db.log_error import save_error_log

from app.agents.article_agent import generate_article
from app.agents.qa_agent import analyze_article


logger = logging.getLogger(__name__)


async def generate_article_task(content_item_id: int) -> None:
    """
    Асинхронная таска генерации статьи.

    Логика:
    1. Получаем content_item
    2. Генерируем статью
    3. Прогоняем через QA
    4. Обновляем content_item
    5. При ошибке — сохраняем лог в error_logs

    Никакой бизнес-логики в DB-слое.
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
                    module="generate_article_task",
                    entity_id=content_item_id,
                    error="Content item not found",
                    severity="high",
                    cause="Invalid content_item_id",
                    recommendation="Check task input and DB integrity",
                )
                await session.commit()
                return

            # --- Генерация статьи ---
            article_text = await generate_article(
                title=content_item.title,
                brief=content_item.brief,
                keywords=content_item.keywords,
            )

            if not article_text:
                raise RuntimeError("Article generation returned empty result")

            # --- QA-анализ ---
            qa_result = await analyze_article(
                title=content_item.title,
                article_text=article_text,
            )

            # --- Обновление контента ---
            await update_content_item(
                session=session,
                content_item_id=content_item_id,
                text=article_text,
                status="ready",
                qa_score=qa_result.get("score"),
                qa_comment=qa_result.get("comment"),
            )

            await session.commit()

            logger.info(
                "Article generated successfully (content_item_id=%s)",
                content_item_id,
            )

        except Exception as e:
            logger.exception(
                "Error while generating article (content_item_id=%s)",
                content_item_id,
            )

            # попытка QA-анализа ошибки (если агент поддерживает)
            qa_error: Optional[dict] = None
            try:
                qa_error = await analyze_article(
                    title="Error during article generation",
                    article_text=str(e),
                )
            except Exception:
                qa_error = None

            await save_error_log(
                session=session,
                module="generate_article_task",
                entity_id=content_item_id,
                error=str(e),
                severity=(qa_error or {}).get("severity", "high"),
                cause=(qa_error or {}).get("cause"),
                recommendation=(qa_error or {}).get("recommendation"),
            )

            await session.rollback()
            await session.commit()
