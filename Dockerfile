FROM python:3.12-slim

# Install system deps: ffmpeg + Chromium for Playwright
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright with Chromium
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Install Node.js (for frontend build)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY sample.html .

# Build frontend
RUN cd frontend && npm install && npm run build

# Create runtime dirs
RUN mkdir -p backend/uploads backend/output

EXPOSE 8000

ENV GEMINI_API_KEY=""
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
