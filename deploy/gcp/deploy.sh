#!/usr/bin/env bash
set -e

# ==============================================================================
# SovereignForge & PrivyCode — Automated Google Cloud Platform (GCP) Deployer
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  SovereignForge & PrivyCode — Production GCP Cloud Deployer    ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Prerequisites Check
echo -e "\n${YELLOW}[1/4] Validating GCP CLI and Terraform tools...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: 'gcloud' CLI is not installed. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: 'terraform' CLI is not installed. Please install Terraform.${NC}"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>'.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Active GCP Project: ${PROJECT_ID}${NC}"

# 2. Provision Infrastructure via Terraform
echo -e "\n${YELLOW}[2/4] Provisioning Cloud SQL, Memorystore Redis, VPC & Cloud Run via Terraform...${NC}"
cd deploy/gcp/terraform
terraform init
terraform apply -auto-approve -var="project_id=${PROJECT_ID}"
cd ../../../

# 3. Build & Deploy Containers via Google Cloud Build
echo -e "\n${YELLOW}[3/4] Building production container images & deploying to Cloud Run...${NC}"
gcloud builds submit --config=deploy/gcp/cloudbuild.yaml .

# 4. Success Summary
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SovereignForge & PrivyCode Successfully Deployed to GCP!    ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "  • Gateway Service:   https://sovereignforge-gateway-${PROJECT_ID}.a.run.app"
echo -e "  • Test Bench:        https://sovereignforge-gateway-${PROJECT_ID}.a.run.app/ui"
echo -e "  • Admin Dashboard:   https://sovereignforge-gateway-${PROJECT_ID}.a.run.app/admin/dashboard"
echo -e "  • VS Code Extension: apps/vscode-extension/privycode-0.1.0.vsix"
echo -e "${GREEN}================================================================${NC}"
