from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ==========================================================
# Модель контента
# ==========================================================
class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)

    # draft / published / error
    status = Column(String(50), default="draft", index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    telegram_posted = Column(Boolean, default=False, nullable=False)
    vk_posted = Column(Boolean, default=False, nullable=False)

    # Связь с логами ошибок
    error_logs = relationship(
    "ErrorLog",
    back_populates="content_item",
    cascade="all, delete-orphan",
    )


    __table_args__ = (
        Index("ix_content_status", "status"),
    )


# ==========================================================
# Логи ошибок QA / генерации
# ==========================================================
class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)

    content_item_id = Column(
        Integer,
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    module = Column(String(100), nullable=True)

    error = Column(Text, nullable=False)

    severity = Column(String(20), default="medium")

    cause = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    content_item = relationship("ContentItem", back_populates="error_logs")
