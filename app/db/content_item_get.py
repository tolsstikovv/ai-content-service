from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem
from app.db.session import async_session_factory


# Получить контент по ID
async def get_content_item_by_id(
    item_id: int
) -> Optional[ContentItem]:
    async with async_session_factory() as session:  # type: AsyncSession
        result = await session.execute(
            select(ContentItem).where(ContentItem.id == item_id)
        )
        return result.scalar_one_or_none()


# Получить все статьи по статусу
async def get_content_items_by_status(
    status: str
) -> List[ContentItem]:
    async with async_session_factory() as session:  # type: AsyncSession
        result = await session.execute(
            select(ContentItem).where(ContentItem.status == status)
        )
        return result.scalars().all()
