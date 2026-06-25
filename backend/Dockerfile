FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg \
    ca-certificates \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium for Playwright
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build frontend if present
RUN if [ -d "../frontend" ]; then \
        cd ../frontend && npm install && npm run build; \
    fi

EXPOSE 8000

ENV GEMINI_API_KEY=""
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
