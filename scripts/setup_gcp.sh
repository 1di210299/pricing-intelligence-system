#!/bin/bash

# Deployment Setup Script for Pricing Intelligence System
# This script helps automate the GCP setup process

set -e  # Exit on error

echo "🚀 Pricing Intelligence Deployment Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI is installed${NC}"

# Prompt for project ID
read -p "Enter GCP Project ID (e.g., pricing-intelligence-prod): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Project ID cannot be empty${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Setting up project: $PROJECT_ID${NC}"
echo ""

# Set project
echo "📋 Setting active project..."
gcloud config set project $PROJECT_ID || {
    echo -e "${RED}❌ Failed to set project. Does it exist?${NC}"
    read -p "Create new project? (y/n): " CREATE_PROJECT
    if [ "$CREATE_PROJECT" = "y" ]; then
        gcloud projects create $PROJECT_ID --name="Pricing Intelligence"
        gcloud config set project $PROJECT_ID
    else
        exit 1
    fi
}

# Enable APIs
echo ""
echo "🔌 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable compute.googleapis.com

echo -e "${GREEN}✅ APIs enabled${NC}"

# Create Artifact Registry repository
echo ""
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create pricing-intelligence \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker images for Pricing Intelligence" \
    || echo "Repository might already exist"

# Prompt for database password
echo ""
read -sp "Enter password for PostgreSQL database: " DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}❌ Database password cannot be empty${NC}"
    exit 1
fi

# Create Cloud SQL instance
echo ""
echo "🗄️  Creating Cloud SQL instance (this may take 5-10 minutes)..."
gcloud sql instances create pricing-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password="$DB_PASSWORD" \
    || echo -e "${YELLOW}Instance might already exist${NC}"

# Create database
echo ""
echo "📊 Creating database..."
gcloud sql databases create pricing_intelligence \
    --instance=pricing-db \
    || echo -e "${YELLOW}Database might already exist${NC}"

# Get connection name
echo ""
echo "🔗 Getting Cloud SQL connection name..."
CONNECTION_NAME=$(gcloud sql instances describe pricing-db --format="value(connectionName)")
echo -e "${GREEN}Connection name: $CONNECTION_NAME${NC}"

# Create service account
echo ""
echo "👤 Creating service account for GitHub Actions..."
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployment" \
    || echo -e "${YELLOW}Service account might already exist${NC}"

SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant roles
echo "🔐 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

# Create service account key
echo ""
echo "🔑 Creating service account key..."
KEY_FILE="github-actions-key.json"
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SA_EMAIL

echo -e "${GREEN}✅ Service account key created: $KEY_FILE${NC}"

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Add these secrets to your GitHub repository:"
echo "   - GCP_PROJECT_ID: $PROJECT_ID"
echo "   - GCP_SA_KEY: (contents of $KEY_FILE)"
echo "   - CLOUD_SQL_CONNECTION_NAME: $CONNECTION_NAME"
echo "   - DATABASE_URL: postgresql://postgres:YOUR_PASSWORD@/pricing_intelligence?host=/cloudsql/$CONNECTION_NAME"
echo "   - OPENAI_API_KEY: (your OpenAI API key)"
echo ""
echo "2. Initialize database schema:"
echo "   gcloud sql connect pricing-db --user=postgres --database=pricing_intelligence"
echo "   Then paste contents of scripts/init.sql"
echo ""
echo "3. Migrate CSV data:"
echo "   export DATABASE_URL=\"postgresql://postgres:$DB_PASSWORD@/pricing_intelligence?host=/cloudsql/$CONNECTION_NAME\""
echo "   python scripts/migrate_csv_to_postgres.py"
echo ""
echo "4. Push to GitHub to trigger deployment:"
echo "   git push origin main"
echo ""
echo "⚠️  IMPORTANT: Keep $KEY_FILE secure and delete it after adding to GitHub secrets!"
echo ""
