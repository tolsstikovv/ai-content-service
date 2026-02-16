import os
import json
from typing import Optional, List, Dict, Any

import aiohttp


# =========================
# Конфигурация
# =========================

QA_PROVIDER = os.getenv("QA_PROVIDER", "openai")  # openai | stub
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_QA_MODEL = os.getenv("OPENAI_QA_MODEL", "gpt-4o-mini")

QA_TIMEOUT = int(os.getenv("QA_TIMEOUT", "90"))


# =========================
# Публичные методы
# =========================

async def analyze_article(
    title: str,
    article_text: str,
) -> Dict[str, Any]:
    """
    QA-анализ статьи.

    Возвращает:
    {
        "score": float (0-10),
        "comment": str,
        "severity": "low|medium|high",
        "cause": str | None,
        "recommendation": str | None
    }
    """

    prompt = _build_article_prompt(title, article_text)

    if QA_PROVIDER == "openai":
        return await _run_openai_qa(prompt)

    if QA_PROVIDER == "stub":
        return _stub_ok()

    raise ValueError(f"Unsupported QA_PROVIDER: {QA_PROVIDER}")


async def analyze_image_generation(
    title: str,
    images: List[str],
) -> Dict[str, Any]:
    """
    QA-анализ генерации изображений.

    images — список URL или описаний ошибок
    """

    prompt = _build_image_prompt(title, images)

    if QA_PROVIDER == "openai":
        return await _run_openai_qa(prompt)

    if QA_PROVIDER == "stub":
        return _stub_ok()

    raise ValueError(f"Unsupported QA_PROVIDER: {QA_PROVIDER}")


# =========================
# Prompt builders
# =========================

def _build_article_prompt(title: str, text: str) -> str:
    excerpt = text[:3000]

    return f"""
You are an automated QA engineer for AI-generated content.

Evaluate the following ARTICLE.

Title:
{title}

Text:
{excerpt}

Check for:
- logical consistency
- factual errors (if obvious)
- structure and readability
- SEO-friendliness
- spam / water / repetition
- safety and policy risks

Respond STRICTLY in valid JSON:

{{
  "score": number from 0 to 10,
  "comment": "short human-readable summary",
  "severity": "low" | "medium" | "high",
  "cause": "main problem if any or null",
  "recommendation": "how to improve or null"
}}
"""


def _build_image_prompt(title: str, images: List[str]) -> str:
    images_block = "\n".join(images[:5])

    return f"""
You are an automated QA engineer for AI-generated images.

Article title:
{title}

Generated images (URLs or error messages):
{images_block}

Check for:
- relevance to article topic
- diversity (not duplicates)
- suitability for social media / blog
- obvious generation failures

Respond STRICTLY in valid JSON:

{{
  "score": number from 0 to 10,
  "comment": "short human-readable summary",
  "severity": "low" | "medium" | "high",
  "cause": "main problem if any or null",
  "recommendation": "how to improve or null"
}}
"""


# =========================
# OpenAI QA runner
# =========================

async def _run_openai_qa(prompt: str) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_QA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict QA system. Output ONLY valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=QA_TIMEOUT),
        ) as response:

            if response.status != 200:
                text = await response.text()
                raise RuntimeError(
                    f"QA OpenAI API error ({response.status}): {text}"
                )

            data = await response.json()

    content = data["choices"][0]["message"]["content"]

    return _safe_parse_response(content)


# =========================
# Helpers
# =========================

def _safe_parse_response(raw: str) -> Dict[str, Any]:
    """
    Гарантирует, что QA всегда вернёт валидную структуру.
    """

    try:
        parsed = json.loads(raw)
    except Exception:
        return {
            "score": 0,
            "comment": "QA response parsing failed",
            "severity": "high",
            "cause": "Invalid JSON from QA model",
            "recommendation": "Inspect QA prompt or provider",
        }

    return {
        "score": float(parsed.get("score", 0)),
        "comment": str(parsed.get("comment", "")),
        "severity": parsed.get("severity", "low"),
        "cause": parsed.get("cause"),
        "recommendation": parsed.get("recommendation"),
    }


def _stub_ok() -> Dict[str, Any]:
    """
    Заглушка для разработки.
    """
    return {
        "score": 9.5,
        "comment": "Looks good (stub QA)",
        "severity": "low",
        "cause": None,
        "recommendation": None,
    }
