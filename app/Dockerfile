# scale-api — my Dockerfile for Assignment 3 (the kit's was the reference).
# Same runtime as the function (Python 3.11) so the two /score answers are comparable.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# requirements first so the pip layer is cached when only main.py changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# don't run as root; --chown because the kit's files arrive mode 700 (root-owned after COPY, unreadable by appuser)
RUN useradd --system --no-create-home appuser
COPY --chown=appuser:appuser main.py .
USER appuser

# 1 worker, 8 threads (same as the kit, so runs stay comparable); --timeout 0 lets Cloud Run own the request timeout.
# exec so gunicorn is PID 1 and gets Cloud Run's SIGTERM directly.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
