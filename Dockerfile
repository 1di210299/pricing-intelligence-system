FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium only, without system deps since we installed manually)
RUN playwright install chromium

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/thrift_sales_12_weeks_with_subcategory.csv ./data/thrift_sales_12_weeks_with_subcategory.csv
COPY data/thrift_sales_12_weeks_with_subcategory.csv ./thrift_sales_12_weeks_with_subcategory.csv

# Download pre-trained ML model from GCS (public bucket)
RUN mkdir -p models && \
    curl -o models/pricing_model.pkl https://storage.googleapis.com/pricing-intelligence-models/pricing_model.pkl && \
    echo "✅ ML model downloaded successfully"

# Create non-root user (but Playwright needs some permissions)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
