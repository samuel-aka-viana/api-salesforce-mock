
FROM python:3.12-slim

LABEL maintainer="Marketing Cloud API Team"
LABEL version="1.0.0"
LABEL description="Salesforce Marketing Cloud API Clone"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    curl \
    wget \
    vim \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    locales \
    && rm -rf /var/lib/apt/lists/*

RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen pt_BR.UTF-8 && \
    update-locale LANG=pt_BR.UTF-8

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads /app/logs /app/instance && \
    chown -R appuser:appuser /app

RUN chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando padrão
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn"]