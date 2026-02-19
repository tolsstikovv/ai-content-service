import os
from typing import Dict

from openai import OpenAI
from loguru import logger


# =========================
# Инициализация клиента
# =========================

def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    return OpenAI(api_key=api_key)


# =========================
# Prompt builder (локальный)
# =========================

def _build_article_prompt(
    title: str,
    description: str,
    style: str,
    platform: str,
    length: str
) -> str:
    """
    Формирует промт для генерации статьи
    """

    return f"""
Ты профессиональный автор контента.

Напиши статью по теме:
"{title}"

Описание темы:
{description}

Требования:
- Стиль: {style}
- Длина: {length}
- Платформа: {platform}
- Структурированный текст
- Без эмодзи
- Без упоминаний ИИ
- Без воды и общих фраз
- Конкретно, полезно, читабельно

Формат:
- Заголовок
- Основной текст
- Абзацы по 3–4 строки
""".strip()


# =========================
# Основная функция агента
# =========================

def generate_article(
    title: str,
    description: str,
    style: str = "информативный",
    platform: str = "telegram",
    length: str = "medium",
    model: str = "gpt-4.1"
) -> Dict[str, str]:
    """
    Генерирует статью по заданным параметрам

    Возвращает:
    {
        "title": str,
        "text": str,
        "model": str
    }
    """

    logger.info(f"[ArticleAgent] Generating article: {title}")

    client = _get_openai_client()

    prompt = _build_article_prompt(
        title=title,
        description=description,
        style=style,
        platform=platform,
        length=length
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты профессиональный редактор и автор статей."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1200,
        )

        article_text = response.choices[0].message.content.strip()

        logger.success("[ArticleAgent] Article generated successfully")

        return {
            "title": title,
            "text": article_text,
            "model": model,
        }

    except Exception as e:
        logger.error(f"[ArticleAgent] Error generating article: {e}")
        raise
