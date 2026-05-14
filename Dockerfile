# ─── Build a slim Python 3.11 image for the FastAPI app ─────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for mysqlclient/pymysql + healthcheck tooling
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first to maximise Docker layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Healthcheck hits /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
