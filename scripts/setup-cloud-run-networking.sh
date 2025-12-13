#!/bin/bash
# Setup script for Cloud Run VPC Connector and internal networking

set -e

PROJECT_ID="${GCP_PROJECT_ID:-vizudev}"
REGION="${GCP_REGION:-southamerica-east1}"

echo "========================================="
echo "Cloud Run Internal Networking Setup"
echo "========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Enable Serverless VPC Access API
echo "Step 1: Enabling Serverless VPC Access API..."
gcloud services enable vpcaccess.googleapis.com \
  --project="$PROJECT_ID" \
  --quiet || echo "✓ API already enabled"

# Step 2: Create VPC Connector using Terraform
echo ""
echo "Step 2: Creating VPC Connector with Terraform..."
cd "$(dirname "$0")/terraform"
terraform init -upgrade
terraform plan -target=google_vpc_access_connector.cloudrun_connector
read -p "Apply Terraform changes? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  terraform apply -target=google_vpc_access_connector.cloudrun_connector -auto-approve
  echo "✓ VPC Connector created"
else
  echo "✗ Skipped VPC Connector creation"
fi

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Trigger GitHub Actions deploy workflow"
echo "2. Services will now use internal VPC networking"
echo "3. Monitor Cloud Run logs for startup issues"
echo ""
