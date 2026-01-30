FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/thrift_sales_12_weeks_with_subcategory.csv ./data/thrift_sales_12_weeks_with_subcategory.csv
COPY data/thrift_sales_12_weeks_with_subcategory.csv ./thrift_sales_12_weeks_with_subcategory.csv

# Download pre-trained ML model from GCS (public bucket)
RUN mkdir -p models && \
    apt-get update && apt-get install -y curl && \
    curl -o models/pricing_model.pkl https://storage.googleapis.com/pricing-intelligence-models/pricing_model.pkl && \
    echo "✅ ML model downloaded successfully" && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
