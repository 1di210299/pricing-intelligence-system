# Quick Start Deployment Guide

This guide will help you deploy the Pricing Intelligence System to Google Cloud Platform with PostgreSQL and GitHub Actions CI/CD.

## Prerequisites

- [Git](https://git-scm.com/) installed
- [GitHub account](https://github.com/)
- [Google Cloud account](https://cloud.google.com/)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed

## Step 1: Test Locally with Docker

First, test the system with PostgreSQL using Docker:

```bash
# Start PostgreSQL and backend
docker-compose up -d

# Wait for database to be ready (about 10 seconds)
sleep 10

# Run migration script
python scripts/migrate_csv_to_postgres.py

# Check the backend logs
docker-compose logs backend

# Test the API
curl http://localhost:8000/health
```

To enable PostgreSQL mode in production, set `USE_DATABASE=true` in your `.env` file.

## Step 2: Initialize Git Repository

```bash
cd /Users/1di/coding_challenge

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - Pricing Intelligence System with OpenAI + PostgreSQL"
```

## Step 3: Create Private GitHub Repository

### Option A: Using GitHub CLI
```bash
# Install GitHub CLI if not already installed
brew install gh

# Login to GitHub
gh auth login

# Create private repository
gh repo create pricing-intelligence-system --private --source=. --remote=origin

# Push code
git push -u origin main
```

### Option B: Using GitHub Website
1. Go to https://github.com/new
2. Repository name: `pricing-intelligence-system`
3. Set to **Private**
4. Click "Create repository"
5. Push your code:
```bash
git remote add origin git@github.com:YOUR_USERNAME/pricing-intelligence-system.git
git branch -M main
git push -u origin main
```

## Step 4: Set Up Google Cloud Project

```bash
# Set your project ID (choose a unique name)
export PROJECT_ID="pricing-intelligence-prod"

# Create new GCP project
gcloud projects create $PROJECT_ID --name="Pricing Intelligence"

# Set as current project
gcloud config set project $PROJECT_ID

# Enable billing (required for Cloud Run and Cloud SQL)
# You need to link a billing account - do this in the GCP Console
# https://console.cloud.google.com/billing/linkedaccount

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com
```

## Step 5: Create Cloud SQL PostgreSQL Instance

```bash
# Create PostgreSQL instance (takes 5-10 minutes)
gcloud sql instances create pricing-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_SECURE_PASSWORD \
    --backup-start-time=03:00

# Create database
gcloud sql databases create pricing_intelligence --instance=pricing-db

# Get connection name
export CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe pricing-db --format="value(connectionName)")
echo "Connection name: $CLOUD_SQL_CONNECTION_NAME"

# Create database user for application
gcloud sql users create pricing_user \
    --instance=pricing-db \
    --password=YOUR_APP_PASSWORD
```

## Step 6: Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create pricing-app \
    --repository-format=docker \
    --location=us-central1 \
    --description="Pricing Intelligence Docker images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Step 7: Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --description="Service account for GitHub Actions deployments" \
    --display-name="GitHub Actions"

# Get service account email
export SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

# Create and download service account key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=$SA_EMAIL

# Display the key (you'll need this for GitHub Secrets)
cat github-actions-key.json
```

## Step 8: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

1. **GCP_PROJECT_ID**
   ```
   pricing-intelligence-prod
   ```

2. **GCP_SA_KEY**
   ```
   (paste contents of github-actions-key.json)
   ```

3. **OPENAI_API_KEY**
   ```
   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
   ```

4. **CLOUD_SQL_CONNECTION_NAME**
   ```
   (use value from: gcloud sql instances describe pricing-db --format="value(connectionName)")
   ```

5. **DATABASE_URL**
   ```
   postgresql://pricing_user:YOUR_APP_PASSWORD@/pricing_intelligence?host=/cloudsql/CONNECTION_NAME
   ```

## Step 9: Deploy to Production

Now push to trigger the deployment:

```bash
git add .
git commit -m "Configure production deployment"
git push origin main
```

The GitHub Actions workflow will:
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run
4. Run database migration

Check deployment status:
- GitHub: Actions tab in your repository
- GCP: https://console.cloud.google.com/run

## Step 10: Get Your Production URL

```bash
# Get Cloud Run service URL
gcloud run services describe pricing-intelligence \
    --platform managed \
    --region us-central1 \
    --format="value(status.url)"
```

## Step 11: Update Frontend Configuration

Update `frontend/.env` with your production URL:

```bash
echo "VITE_API_URL=https://your-cloud-run-url.run.app" > frontend/.env
```

## Testing Your Production Deployment

```bash
# Test health endpoint
curl https://your-cloud-run-url.run.app/health

# Test price recommendation
curl -X POST https://your-cloud-run-url.run.app/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{"upc": "Columbia Jacket"}'
```

## Monitoring and Logs

### View Cloud Run Logs
```bash
gcloud run services logs read pricing-intelligence \
    --region=us-central1 \
    --limit=50
```

### View Database Logs
```bash
gcloud sql operations list --instance=pricing-db --limit=10
```

### Check Database Connection
```bash
# Connect to database
gcloud sql connect pricing-db --user=postgres --database=pricing_intelligence

# Run query to verify data
SELECT COUNT(*) FROM sales_data;
SELECT COUNT(*) FILTER (WHERE sold_date IS NOT NULL) as sold_items FROM sales_data;
```

## Updating Your Deployment

Any push to the `main` branch will automatically trigger a new deployment:

```bash
# Make changes to your code
git add .
git commit -m "Your update message"
git push origin main

# GitHub Actions will automatically deploy
```

## Cost Management

Estimated monthly costs:
- Cloud Run (minimal traffic): $0-5
- Cloud SQL (db-f1-micro): $7-10
- Artifact Registry: $0-2
- **Total: $7-17/month**

To minimize costs:
- Cloud SQL stops charging when idle
- Cloud Run scales to zero when not used
- Delete old container images regularly

## Cleanup (if needed)

To delete all resources:

```bash
# Delete Cloud Run service
gcloud run services delete pricing-intelligence --region=us-central1

# Delete Cloud SQL instance
gcloud sql instances delete pricing-db

# Delete Artifact Registry repository
gcloud artifacts repositories delete pricing-app --location=us-central1

# Delete service account
gcloud iam service-accounts delete $SA_EMAIL
```

## Troubleshooting

### GitHub Actions fails
- Check Secrets are configured correctly
- Verify service account has correct permissions
- Check Actions logs for specific errors

### Cloud Run service won't start
- Check environment variables are set
- Verify Cloud SQL connection name is correct
- Check service logs: `gcloud run services logs read pricing-intelligence --region=us-central1`

### Database migration fails
- Verify DATABASE_URL format
- Check Cloud SQL instance is running
- Ensure pricing_user has correct permissions

### OpenAI API errors
- Verify OPENAI_API_KEY is valid
- Check API quota limits
- Review backend logs for specific error messages

## Support

For issues or questions:
1. Check logs in GitHub Actions
2. Check Cloud Run logs
3. Check Cloud SQL logs
4. Review README_PRODUCTION.md for architecture details

## Next Steps

- Set up custom domain for Cloud Run
- Configure Cloud CDN for frontend
- Set up monitoring alerts
- Configure backup retention policies
- Implement rate limiting
- Add authentication/authorization
