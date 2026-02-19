import os
import hashlib
from typing import List

import aiohttp


# =========================
# Конфигурация
# =========================

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "openai")  # openai | stub
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1024x1024")
IMAGE_QUALITY = os.getenv("IMAGE_QUALITY", "standard")


# =========================
# Публичный интерфейс агента
# =========================

async def generate_images(
    title: str,
    article_text: str,
    style: str,
    count: int = 1,
) -> List[str]:
    """
    Генерирует изображения под статью.

    Возвращает:
    - список URL изображений
    - либо пустой список (если провайдер вернул ошибку)

    Исключения:
    - пробрасываются вверх (таска сама решает, что с ними делать)
    """

    prompt = _build_prompt(
        title=title,
        article_text=article_text,
        style=style,
    )

    if IMAGE_PROVIDER == "openai":
        return await _generate_openai(prompt, count)

    if IMAGE_PROVIDER == "stub":
        return _generate_stub(prompt, count)

    raise ValueError(f"Unsupported IMAGE_PROVIDER: {IMAGE_PROVIDER}")


# =========================
# Prompt builder
# =========================

def _build_prompt(title: str, article_text: str, style: str) -> str:
    """
    Формирует prompt для генерации изображения.
    """

    base = article_text[:1500]  # защита от слишком длинного контекста

    return (
        f"Create a high-quality illustration for an article.\n\n"
        f"Title: {title}\n\n"
        f"Context:\n{base}\n\n"
        f"Visual style: {style}\n"
        f"Requirements:\n"
        f"- No text on image\n"
        f"- Professional composition\n"
        f"- Suitable for social media and blog preview\n"
    )


# =========================
# OpenAI provider
# =========================

async def _generate_openai(prompt: str, count: int) -> List[str]:
    """
    Генерация изображений через OpenAI Images API.
    """

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_IMAGE_MODEL,
        "prompt": prompt,
        "size": IMAGE_SIZE,
        "quality": IMAGE_QUALITY,
        "n": count,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:

            if response.status != 200:
                text = await response.text()
                raise RuntimeError(
                    f"OpenAI image API error ({response.status}): {text}"
                )

            data = await response.json()

    images = []
    for item in data.get("data", []):
        url = item.get("url")
        if url:
            images.append(url)

    return images


# =========================
# Stub provider (dev / tests)
# =========================

def _generate_stub(prompt: str, count: int) -> List[str]:
    """
    Заглушка для разработки и тестов.
    Генерирует фейковые URL.
    """

    base_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

    return [
        f"https://stub.images/{base_hash}_{i}.png"
        for i in range(1, count + 1)
    ]
