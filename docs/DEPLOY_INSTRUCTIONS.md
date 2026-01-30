# Deployment Instructions

## Prerequisites

- GitHub account
- Google Cloud Platform (GCP) account with billing enabled
- `gcloud` CLI installed
- Docker installed (for local testing)

## Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Test local import
python3 -c "from app.main import app; print('✅ Import successful')"
```

## Step 2: Create GitHub Repository

```bash
# Initialize git (if not already initialized)
cd /Users/1di/coding_challenge
git init
git add .
git commit -m "Initial commit - UPC Pricing Intelligence System"

# Create private repository on GitHub via CLI or web interface
# Then push:
git remote add origin git@github.com:YOUR_USERNAME/pricing-intelligence.git
git branch -M main
git push -u origin main
```

## Step 3: Set up Google Cloud Platform

### 3.1 Create GCP Project

```bash
# Set project ID
export PROJECT_ID="pricing-intelligence-prod"

# Create project
gcloud projects create $PROJECT_ID --name="Pricing Intelligence"

# Set as active project
gcloud config set project $PROJECT_ID

# Link billing account (replace with your billing account ID)
gcloud billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 3.2 Enable Required APIs

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Cloud SQL API
gcloud services enable sqladmin.googleapis.com

# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Enable Compute Engine API (for Cloud SQL)
gcloud services enable compute.googleapis.com
```

### 3.3 Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create pricing-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create pricing_intelligence \
    --instance=pricing-db

# Get connection name (needed for GitHub secrets)
gcloud sql instances describe pricing-db --format="value(connectionName)"
# Save this output - it looks like: PROJECT_ID:REGION:INSTANCE_NAME
```

### 3.4 Initialize Database Schema

```bash
# Connect to Cloud SQL instance
gcloud sql connect pricing-db --user=postgres --database=pricing_intelligence

# Once connected, paste the contents of scripts/init.sql
# Or run:
psql -U postgres -d pricing_intelligence -f scripts/init.sql
```

### 3.5 Migrate CSV Data to PostgreSQL

```bash
# Set database URL
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@/pricing_intelligence?host=/cloudsql/PROJECT_ID:us-central1:pricing-db"

# Run migration script
python scripts/migrate_csv_to_postgres.py
```

### 3.6 Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployment"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@${PROJECT_ID}.iam.gserviceaccount.com

# Display the key (you'll need to copy this for GitHub secrets)
cat github-actions-key.json
```

## Step 4: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

1. **GCP_PROJECT_ID**
   - Value: `pricing-intelligence-prod` (your project ID)

2. **GCP_SA_KEY**
   - Value: Contents of `github-actions-key.json` (entire JSON file)

3. **OPENAI_API_KEY**
   - Value: `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`

4. **CLOUD_SQL_CONNECTION_NAME**
   - Value: `PROJECT_ID:us-central1:pricing-db` (from step 3.3)

5. **DATABASE_URL**
   - Value: `postgresql://postgres:YOUR_PASSWORD@/pricing_intelligence?host=/cloudsql/PROJECT_ID:us-central1:pricing-db`

## Step 5: Enable Database in Production

Update your `.env` file for production (or set environment variables in Cloud Run):

```bash
USE_DATABASE=true
DATABASE_URL=<your_cloud_sql_connection_string>
```

## Step 6: Trigger Deployment

```bash
# Push to main branch to trigger deployment
git add .
git commit -m "Configure production deployment"
git push origin main
```

GitHub Actions will automatically:
1. Build Docker image
2. Push to Google Artifact Registry
3. Deploy to Cloud Run
4. Run database migrations

## Step 7: Verify Deployment

```bash
# Get Cloud Run service URL
gcloud run services describe pricing-intelligence \
    --region=us-central1 \
    --format="value(status.url)"

# Test the health endpoint
curl https://YOUR-CLOUD-RUN-URL/health

# Test price recommendation
curl -X POST https://YOUR-CLOUD-RUN-URL/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{"upc": "Nike Sneakers"}'
```

## Local Testing with PostgreSQL

To test locally with PostgreSQL before deploying:

```bash
# Start PostgreSQL with Docker Compose
docker-compose up -d db

# Wait for PostgreSQL to start
sleep 10

# Run migration
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/pricing_intelligence"
python scripts/migrate_csv_to_postgres.py

# Update .env
echo "USE_DATABASE=true" >> .env

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Cost Estimation

- **Cloud Run**: ~$5-10/month (1 instance, minimal traffic)
- **Cloud SQL**: ~$10-15/month (db-f1-micro instance)
- **Artifact Registry**: ~$0.10/month (storage)
- **OpenAI API**: Variable (depends on usage)

**Total**: ~$15-30/month for production deployment

## Monitoring

```bash
# View Cloud Run logs
gcloud run services logs read pricing-intelligence \
    --region=us-central1 \
    --limit=50

# View Cloud SQL logs
gcloud sql operations list --instance=pricing-db

# Monitor GitHub Actions
# Go to: https://github.com/YOUR_USERNAME/pricing-intelligence/actions
```

## Rollback

If deployment fails:

```bash
# Roll back to previous revision
gcloud run services update-traffic pricing-intelligence \
    --region=us-central1 \
    --to-revisions=PREVIOUS_REVISION=100
```

## Cleanup (if needed)

```bash
# Delete Cloud Run service
gcloud run services delete pricing-intelligence --region=us-central1

# Delete Cloud SQL instance
gcloud sql instances delete pricing-db

# Delete project (WARNING: This deletes everything!)
gcloud projects delete $PROJECT_ID
```

## Troubleshooting

### Database Connection Issues

```bash
# Check Cloud SQL instance status
gcloud sql instances describe pricing-db

# Test connection from Cloud Run
gcloud run services describe pricing-intelligence \
    --region=us-central1 \
    --format="value(status.conditions)"
```

### GitHub Actions Failures

1. Check logs in GitHub Actions tab
2. Verify all secrets are set correctly
3. Ensure service account has proper permissions
4. Check GCP API quotas

### Application Errors

```bash
# View detailed logs
gcloud run services logs tail pricing-intelligence --region=us-central1

# Check environment variables
gcloud run services describe pricing-intelligence \
    --region=us-central1 \
    --format="value(spec.template.spec.containers[0].env)"
```

## Support

For issues:
1. Check GitHub Actions logs
2. Check Cloud Run logs: `gcloud run services logs read`
3. Verify all environment variables are set
4. Test locally with Docker Compose first
