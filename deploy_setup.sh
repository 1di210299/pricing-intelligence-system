#!/bin/bash

# Deployment Setup Script for Pricing Intelligence System
# This script helps set up the production deployment on Google Cloud Platform

set -e  # Exit on any error

echo "🚀 Pricing Intelligence System - Deployment Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it from https://cloud.google.com/sdk/docs/install"
    exit 1
fi
print_success "gcloud CLI is installed"

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "git is not installed. Please install it from https://git-scm.com/"
    exit 1
fi
print_success "git is installed"

# Check if docker is installed (optional)
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
else
    print_warning "Docker is not installed (optional for local testing)"
fi

echo ""
echo "=================================================="
echo "Step 1: Test Locally (Optional)"
echo "=================================================="
echo ""
echo "Would you like to test the system locally with Docker first? (y/n)"
read -r test_local

if [[ "$test_local" == "y" ]]; then
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required for local testing"
        exit 1
    fi
    
    echo "Starting PostgreSQL with Docker..."
    docker-compose up -d
    
    echo "Waiting for database to be ready..."
    sleep 10
    
    echo "Running database migration..."
    python3 scripts/migrate_csv_to_postgres.py
    
    print_success "Local system is running at http://localhost:8000"
    echo "Test with: curl http://localhost:8000/health"
    echo ""
    echo "Press Enter to continue with cloud deployment..."
    read -r
fi

echo ""
echo "=================================================="
echo "Step 2: Configure GCP Project"
echo "=================================================="
echo ""

# Get project ID
echo "Enter your GCP Project ID (or a new one to create):"
read -r PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID cannot be empty"
    exit 1
fi

echo "Setting GCP project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" 2>/dev/null || {
    echo "Project doesn't exist. Creating new project..."
    gcloud projects create "$PROJECT_ID" --name="Pricing Intelligence"
    gcloud config set project "$PROJECT_ID"
}
print_success "GCP project configured"

echo ""
echo "⚠️  IMPORTANT: You need to enable billing for this project"
echo "   Visit: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "   Press Enter after enabling billing..."
read -r

echo ""
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com

print_success "APIs enabled"

echo ""
echo "=================================================="
echo "Step 3: Create Cloud SQL Instance"
echo "=================================================="
echo ""

echo "Enter a secure password for the PostgreSQL root user:"
read -rs ROOT_PASSWORD
echo ""

echo "Creating Cloud SQL instance (this takes 5-10 minutes)..."
gcloud sql instances create pricing-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password="$ROOT_PASSWORD" \
    --backup-start-time=03:00

print_success "Cloud SQL instance created"

echo "Creating database..."
gcloud sql databases create pricing_intelligence --instance=pricing-db

echo "Enter a password for the application database user:"
read -rs APP_PASSWORD
echo ""

gcloud sql users create pricing_user \
    --instance=pricing-db \
    --password="$APP_PASSWORD"

print_success "Database and user created"

# Get connection name
CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe pricing-db --format="value(connectionName)")
echo ""
print_success "Cloud SQL Connection Name: $CLOUD_SQL_CONNECTION_NAME"

echo ""
echo "=================================================="
echo "Step 4: Create Artifact Registry"
echo "=================================================="
echo ""

gcloud artifacts repositories create pricing-app \
    --repository-format=docker \
    --location=us-central1 \
    --description="Pricing Intelligence Docker images"

gcloud auth configure-docker us-central1-docker.pkg.dev

print_success "Artifact Registry configured"

echo ""
echo "=================================================="
echo "Step 5: Create Service Account"
echo "=================================================="
echo ""

SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create github-actions \
    --description="Service account for GitHub Actions deployments" \
    --display-name="GitHub Actions"

echo "Granting permissions..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

echo "Creating service account key..."
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account="$SA_EMAIL"

print_success "Service account created and key saved to github-actions-key.json"

echo ""
echo "=================================================="
echo "Step 6: GitHub Secrets Configuration"
echo "=================================================="
echo ""

DATABASE_URL="postgresql://pricing_user:${APP_PASSWORD}@/pricing_intelligence?host=/cloudsql/${CLOUD_SQL_CONNECTION_NAME}"

echo "Add these secrets to your GitHub repository:"
echo "(Settings → Secrets and variables → Actions → New repository secret)"
echo ""
echo "1. GCP_PROJECT_ID"
echo "   ${PROJECT_ID}"
echo ""
echo "2. GCP_SA_KEY"
echo "   (Paste contents of github-actions-key.json below)"
cat github-actions-key.json
echo ""
echo ""
echo "3. OPENAI_API_KEY"
echo "   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"
echo ""
echo "4. CLOUD_SQL_CONNECTION_NAME"
echo "   ${CLOUD_SQL_CONNECTION_NAME}"
echo ""
echo "5. DATABASE_URL"
echo "   ${DATABASE_URL}"
echo ""
echo ""

# Save configuration
cat > deployment-config.txt <<EOF
GCP_PROJECT_ID=${PROJECT_ID}
CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}
DATABASE_URL=${DATABASE_URL}
SERVICE_ACCOUNT=${SA_EMAIL}
EOF

print_success "Configuration saved to deployment-config.txt"

echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Add the GitHub secrets shown above"
echo "2. Initialize git and push to GitHub:"
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit - Pricing Intelligence System'"
echo "   git remote add origin git@github.com:YOUR_USERNAME/pricing-intelligence-system.git"
echo "   git push -u origin main"
echo ""
echo "3. GitHub Actions will automatically deploy your application"
echo ""
echo "4. Get your service URL:"
echo "   gcloud run services describe pricing-intelligence --platform managed --region us-central1 --format='value(status.url)'"
echo ""
print_warning "SECURITY: Delete github-actions-key.json after adding to GitHub Secrets"
echo "rm github-actions-key.json"
echo ""
