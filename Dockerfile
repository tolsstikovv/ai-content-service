# -----------------------------
# Базовый образ
# -----------------------------
FROM python:3.11-slim

# -----------------------------
# Переменные окружения
# -----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PYTHONPATH=/app

# -----------------------------
# Рабочая директория
# -----------------------------
WORKDIR /app

# -----------------------------
# Установка системных зависимостей
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        gcc \
        g++ \
        wget \
        && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Копирование зависимостей Python
# -----------------------------
COPY requirements.txt .

# -----------------------------
# Установка pip и зависимостей Python
# -----------------------------
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Копирование проекта
# -----------------------------
COPY ./app ./app
COPY ./worker ./worker
COPY ./scheduler ./scheduler

# -----------------------------
# По умолчанию CMD для backend (можно переопределять в docker-compose)
# -----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
