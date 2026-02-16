from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ErrorLog


async def save_error_log(
    session: AsyncSession,
    module: str,
    error: str,
    entity_id: Optional[int] = None,
    severity: Optional[str] = "medium",
    cause: Optional[str] = None,
    recommendation: Optional[str] = None,
) -> ErrorLog:
    """
    Сохраняет лог ошибки в БД.

    ВАЖНО:
    - Не делает commit
    - Не делает rollback
    - Работает в рамках текущей транзакции

    Commit / rollback обязан выполнять вызывающий код.

    :param session: AsyncSession
    :param module: имя модуля / таски / сервиса
    :param error: текст ошибки
    :param entity_id: ID связанной сущности
    :param severity: low / medium / high
    :param cause: предполагаемая причина
    :param recommendation: рекомендация
    :return: созданный объект ErrorLog
    """

    error_log = ErrorLog(
        module=module,
        entity_id=entity_id,
        error=error,
        severity=severity,
        cause=cause,
        recommendation=recommendation,
    )

    session.add(error_log)

    # flush нужен если тебе сразу нужен ID
    await session.flush()

    return error_log
