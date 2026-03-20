#!/bin/bash
# ──────────────────────────────────────────────────────────────
# West Hants Padel Matchmaker – Azure Deployment Script
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ─── Configuration ──────────────────────────────────────────────
APP_NAME="${APP_NAME:-whpadel}"
RESOURCE_GROUP="${RESOURCE_GROUP:-${APP_NAME}-rg}"
LOCATION="${LOCATION:-uksouth}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD environment variable}"

echo "╔══════════════════════════════════════════════════╗"
echo "║  Deploying West Hants Padel to Azure             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  App Name:        $APP_NAME"
echo "  Resource Group:  $RESOURCE_GROUP"
echo "  Location:        $LOCATION"
echo ""

# ─── Step 1: Create Resource Group ──────────────────────────────
echo "▸ Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ─── Step 2: Deploy Infrastructure (Bicep) ─────────────────────
echo "▸ Deploying infrastructure..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters appName="$APP_NAME" \
               postgresAdminPassword="$POSTGRES_PASSWORD" \
  --query 'properties.outputs' \
  --output json)

ACR_NAME=$(echo "$DEPLOY_OUTPUT" | jq -r '.acrName.value')
ACR_LOGIN_SERVER=$(echo "$DEPLOY_OUTPUT" | jq -r '.acrLoginServer.value')
WEB_APP_NAME=$(echo "$DEPLOY_OUTPUT" | jq -r '.webAppName.value')
WEB_APP_URL=$(echo "$DEPLOY_OUTPUT" | jq -r '.webAppUrl.value')

echo "  ACR:      $ACR_LOGIN_SERVER"
echo "  Web App:  $WEB_APP_NAME"

# ─── Step 3: Build & Push Docker Image ─────────────────────────
echo "▸ Building and pushing Docker image..."
az acr login --name "$ACR_NAME"

docker build -t "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" .
docker push "${ACR_LOGIN_SERVER}/${APP_NAME}:latest"

# ─── Step 4: Restart Web App ───────────────────────────────────
echo "▸ Restarting web app..."
az webapp restart \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP"

# ─── Done ───────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Deployment complete!                            ║"
echo "║                                                  ║"
echo "  URL: $WEB_APP_URL"
echo "╚══════════════════════════════════════════════════╝"
