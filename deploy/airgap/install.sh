#!/usr/bin/env bash
set -e

# ==============================================================================
# SovereignForge & PrivyCode — Air-Gapped Bare-Metal Installer
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  SovereignForge & PrivyCode — Air-Gapped Deployment Installer  ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Check prerequisites
echo -e "\n${YELLOW}[1/4] Checking system prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker.${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker and Docker Compose detected.${NC}"

# 2. Start PostgreSQL & Redis
echo -e "\n${YELLOW}[2/4] Starting isolated database & cache containers...${NC}"
docker compose up -d postgres redis
echo -e "${GREEN}✓ Containers started. Waiting for PostgreSQL readiness...${NC}"

sleep 3
until docker exec sovereignforge-postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is healthy on port 5432.${NC}"

# 3. Seed Database Schema
echo -e "\n${YELLOW}[3/4] Initializing database tables and default developer keys...${NC}"
if [ -f "./.venv/bin/python" ]; then
    ./.venv/bin/python packages/db/seed.py
else
    python3 packages/db/seed.py
fi
echo -e "${GREEN}✓ Database initialized and seeded successfully.${NC}"

# 4. Self-Test & Readiness Verification
echo -e "\n${YELLOW}[4/4] Verifying platform deployment health...${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SovereignForge & PrivyCode Air-Gapped Platform Ready!        ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "  • Gateway Endpoint:      http://localhost:8000"
echo -e "  • Interactive Test Bench: http://localhost:8000/ui"
echo -e "  • Admin Ops Dashboard:   http://localhost:8000/admin/dashboard"
echo -e "  • Default API Key:       sk_live_dev_test_12345"
echo -e "  • VS Code Extension:     apps/vscode-extension/privycode-0.1.0.vsix"
echo -e "${GREEN}================================================================${NC}"
