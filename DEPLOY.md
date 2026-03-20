# Azure Deployment Guide – West Hants Padel Matchmaker

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Azure Resource Group             │
│                                                  │
│  ┌──────────────┐   ┌────────────────────────┐  │
│  │  Container    │   │  App Service (Linux)   │  │
│  │  Registry     │──>│  Docker container      │  │
│  │  (ACR)        │   │  Python + static files │  │
│  └──────────────┘   └──────────┬─────────────┘  │
│                                │                 │
│                     ┌──────────▼─────────────┐   │
│                     │  PostgreSQL Flexible    │   │
│                     │  Server (Burstable B1)  │   │
│                     │  Database: padel        │   │
│                     └────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │  Log Analytics Workspace (monitoring)    │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`)
- [Docker](https://docs.docker.com/get-docker/) installed and running
- [Bicep CLI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/install) (bundled with Azure CLI v2.20+)

## Quick Deploy

### PowerShell (Windows)

```powershell
.\deploy.ps1 -PostgresPassword "YourSecurePassword123!"
```

With custom options:

```powershell
.\deploy.ps1 -AppName "mypadel" -Location "uksouth" -PostgresPassword "YourSecurePassword123!"
```

### Bash (Linux/macOS/WSL)

```bash
export POSTGRES_PASSWORD="YourSecurePassword123!"
bash deploy.sh
```

With custom options:

```bash
APP_NAME="mypadel" LOCATION="uksouth" POSTGRES_PASSWORD="YourSecurePassword123!" bash deploy.sh
```

## Step-by-Step Manual Deployment

### 1. Create Resource Group

```bash
az group create --name whpadel-rg --location uksouth
```

### 2. Deploy Infrastructure

```bash
az deployment group create \
  --resource-group whpadel-rg \
  --template-file infra/main.bicep \
  --parameters appName=whpadel postgresAdminPassword="YourSecurePassword123!"
```

### 3. Build and Push Container Image

```bash
# Get ACR name from deployment output
ACR_NAME=$(az deployment group show \
  --resource-group whpadel-rg \
  --name main \
  --query 'properties.outputs.acrName.value' -o tsv)

# Login to ACR
az acr login --name $ACR_NAME

# Build and push
ACR_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
docker build -t $ACR_SERVER/whpadel:latest .
docker push $ACR_SERVER/whpadel:latest
```

### 4. Restart the Web App

```bash
az webapp restart --name whpadel-app --resource-group whpadel-rg
```

## Configuration

### Environment Variables (set automatically by Bicep)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `PORT` | Server listen port (8000) |
| `WEBSITES_PORT` | Azure App Service port mapping |
| `SMTP_HOST` | SMTP server for verification emails |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password or API key |
| `SMTP_FROM` | Sender email address |

### Bicep Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `appName` | (required) | Base name for all resources |
| `location` | Resource group location | Azure region |
| `postgresAdminUser` | `padeladmin` | PostgreSQL admin username |
| `postgresAdminPassword` | (required) | PostgreSQL admin password |
| `appServiceSku` | `B1` | App Service Plan tier |
| `postgresSku` | `Standard_B1ms` | PostgreSQL compute tier |
| `postgresStorageGB` | `32` | PostgreSQL storage size |
| `smtpHost` | `''` | SMTP server for emails |
| `smtpPort` | `587` | SMTP port |
| `smtpUser` | `''` | SMTP username |
| `smtpPassword` | `''` | SMTP password |
| `smtpFrom` | `''` | Sender email address |

## Local Development

The app continues to work locally without any Azure dependencies:

```bash
python server.py
```

When no `DATABASE_URL` environment variable is set, the app automatically uses SQLite (`padel.db`), exactly as before.

When no `SMTP_HOST` is set, verification codes are printed to the console (dev mode) instead of being emailed.

## Estimated Monthly Cost (UK South)

| Resource | SKU | ~Cost/month |
|----------|-----|-------------|
| App Service Plan | B1 | £10 |
| PostgreSQL Flexible | B1ms | £12 |
| Container Registry | Basic | £4 |
| Log Analytics | Per-GB | £2 |
| **Total** | | **~£28** |

*Prices are approximate and may vary. Check [Azure Pricing Calculator](https://azure.microsoft.com/en-gb/pricing/calculator/) for current rates.*

## Updating the App

After making code changes, rebuild and push the container:

```bash
az acr login --name <acr-name>
docker build -t <acr-server>/whpadel:latest .
docker push <acr-server>/whpadel:latest
az webapp restart --name whpadel-app --resource-group whpadel-rg
```

## Tear Down

To remove all Azure resources:

```bash
az group delete --name whpadel-rg --yes --no-wait
```
