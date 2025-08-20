# SOAPify Dockerfile (final, conflict-free)
FROM python:3.11-slim

# Env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Workdir
WORKDIR /app

# System deps (PostgreSQL client headers, crypto, curl, Cairo/Pango stack for PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libjpeg62-turbo \
    libpng16-16 \
    fonts-dejavu \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Python deps (layered caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Create static/media dirs
RUN mkdir -p /app/staticfiles /app/media

# Non-root user
RUN groupadd -r soapify && useradd -r -g soapify soapify \
    && chown -R soapify:soapify /app
USER soapify

# Healthcheck (نیاز به /healthz در Django)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Expose
EXPOSE 8000

# Entrypoint (migrate + collectstatic + gunicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
