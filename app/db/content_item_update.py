from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem


async def get_content_item_by_id(
    session: AsyncSession,
    content_item_id: int
) -> Optional[ContentItem]:
    """
    Получить ContentItem по ID.

    Возвращает:
    - ORM объект ContentItem
    - None, если не найден
    """

    result = await session.execute(
        select(ContentItem).where(ContentItem.id == content_item_id)
    )

    return result.scalar_one_or_none()


async def update_content_item(
    session: AsyncSession,
    content_item_id: int,
    **fields: Any
) -> Optional[ContentItem]:
    """
    Обновить ContentItem по ID.

    :param session: AsyncSession
    :param content_item_id: ID записи
    :param fields: поля для обновления (keyword arguments)

    Пример:
        await update_content_item(
            session,
            1,
            status="done",
            text="Generated text"
        )

    Возвращает:
    - Обновленный ORM объект
    - None, если запись не найдена
    """

    content_item = await get_content_item_by_id(session, content_item_id)

    if not content_item:
        return None

    for field, value in fields.items():
        if hasattr(content_item, field):
            setattr(content_item, field, value)

    await session.commit()
    await session.refresh(content_item)

    return content_item
