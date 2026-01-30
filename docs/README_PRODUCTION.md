# Pricing Intelligence System

Production-ready price recommendation system using market data (eBay via OpenAI web search) and internal sales data (PostgreSQL).

## Features

- 🔍 Real-time eBay price scraping via OpenAI Web Search
- 📊 PostgreSQL database for internal sales analytics
- 🤖 Smart price recommendations using combined data sources
- 🎨 Clean, minimalist React frontend
- 🚀 Auto-deployment to GCP Cloud Run via GitHub Actions
- 🐳 Docker containerized for easy deployment

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- PostgreSQL (Cloud SQL)
- OpenAI API with Web Search
- Pydantic for validation

**Frontend:**
- React 18
- Vite
- Axios

**Infrastructure:**
- Google Cloud Run
- Google Cloud SQL (PostgreSQL)
- GitHub Actions CI/CD
- Docker

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- OpenAI API key

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials:
# - OPENAI_API_KEY=your_key
# - DATABASE_URL=postgresql://user:pass@localhost:5432/pricing_db

# Run migrations
python scripts/migrate_csv_to_postgres.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Access the app at `http://localhost:3000`

## Database Schema

```sql
CREATE TABLE sales_data (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    department VARCHAR(50),
    category VARCHAR(50),
    subcategory VARCHAR(50),
    brand VARCHAR(100),
    production_date DATE,
    sold_date DATE,
    days_to_sell INTEGER,
    production_price DECIMAL(10, 2),
    sold_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_brand ON sales_data(brand);
CREATE INDEX idx_category ON sales_data(category);
CREATE INDEX idx_subcategory ON sales_data(subcategory);
```

## Deployment to GCP

### One-Time Setup

1. **Create GCP Project**
```bash
gcloud projects create pricing-intelligence-prod
gcloud config set project pricing-intelligence-prod
```

2. **Enable APIs**
```bash
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

3. **Create Cloud SQL Instance**
```bash
gcloud sql instances create pricing-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1
```

4. **Create Database**
```bash
gcloud sql databases create pricing_intelligence \
  --instance=pricing-db
```

5. **Set Database Password**
```bash
gcloud sql users set-password postgres \
  --instance=pricing-db \
  --password=YOUR_SECURE_PASSWORD
```

6. **Create Service Account**
```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

gcloud projects add-iam-policy-binding pricing-intelligence-prod \
  --member="serviceAccount:github-actions@pricing-intelligence-prod.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

7. **Generate Key**
```bash
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=github-actions@pricing-intelligence-prod.iam.gserviceaccount.com
```

### GitHub Secrets

Add these secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_SA_KEY`: Contents of `gcp-key.json`
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: Your OpenAI API key

### Deploy

Simply push to `main` branch:

```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

GitHub Actions will automatically:
1. Build Docker image
2. Push to Google Artifact Registry
3. Deploy to Cloud Run
4. Migrate database if needed

## API Documentation

### POST /price-recommendation

Get price recommendation for a product.

**Request:**
```json
{
  "upc": "Nike Sneakers"
}
```

**Response:**
```json
{
  "upc": "Nike Sneakers",
  "recommended_price": 36.63,
  "confidence_score": 80,
  "market_data": {
    "median_price": 75.0,
    "sample_size": 200
  },
  "internal_data": {
    "internal_price": 15.97,
    "sell_through_rate": 0.77
  }
}
```

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# API Config (optional)
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## Architecture

```
┌─────────────┐         ┌──────────────┐
│   React     │────────▶│   FastAPI    │
│  Frontend   │◀────────│   Backend    │
└─────────────┘         └──────┬───────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
              ┌─────▼────┐ ┌──▼─────┐ ┌─▼────────┐
              │PostgreSQL│ │ OpenAI │ │  Cache   │
              │Cloud SQL │ │Web API │ │ (Memory) │
              └──────────┘ └────────┘ └──────────┘
```

## Cost Estimation (Monthly)

- Cloud Run: ~$5-10 (low traffic)
- Cloud SQL (db-f1-micro): ~$7.50
- OpenAI API: Variable ($0.15 per 1K requests)
- **Total: ~$15-30/month for low traffic**

## Monitoring

View logs:
```bash
gcloud run services logs read pricing-intelligence --limit=50
```

## License

MIT

## Support

For issues, please open a GitHub issue or contact support.
