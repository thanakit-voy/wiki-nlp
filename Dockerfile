# syntax=docker/dockerfile:1

# Base image with Python 3.12.10
FROM python:3.12.10-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root user for better security
RUN adduser --disabled-password --gecos "" appuser

# Install dependencies (none by default, but set up the layer for caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Ensure our src is on PYTHONPATH
ENV PYTHONPATH=/app/src

# Drop privileges
USER appuser

# Run as a module so __main__.py executes
ENTRYPOINT ["python", "-m", "app"]

# Default args (can be overridden by `docker run ... -- <args>`)
CMD ["--name", "world"]
