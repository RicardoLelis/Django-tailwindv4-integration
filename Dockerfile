# Multi-stage Dockerfile for Django + Tailwind CSS v4

# Stage 1: Node.js build stage for Tailwind CSS
FROM node:20-alpine AS tailwind-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source CSS file
COPY project/static/src ./project/static/src

# Build Tailwind CSS
RUN npx tailwindcss -i ./project/static/src/styles.css -o ./project/static/dist/styles.css --minify

# Stage 2: Python build stage
FROM python:3.11-slim AS python-builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 3: Final runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r django && useradd -r -g django django

WORKDIR /app

# Copy virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv

# Copy built CSS from tailwind-builder
COPY --from=tailwind-builder /app/project/static/dist ./project/static/dist

# Copy application code
COPY --chown=django:django . .

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "project.wsgi:application"]