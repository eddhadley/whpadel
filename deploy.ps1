# ──────────────────────────────────────────────────────────────
# West Hants Padel Matchmaker – Azure Deployment (PowerShell)
# ──────────────────────────────────────────────────────────────

param(
    [string]$AppName = "whpadel",
    [string]$ResourceGroup = "",
    [string]$Location = "uksouth",
    [Parameter(Mandatory=$true)]
    [string]$PostgresPassword
)

$ErrorActionPreference = "Stop"

if (-not $ResourceGroup) { $ResourceGroup = "$AppName-rg" }

Write-Host ""
Write-Host "  Deploying West Hants Padel to Azure" -ForegroundColor Cyan
Write-Host "  App Name:        $AppName"
Write-Host "  Resource Group:  $ResourceGroup"
Write-Host "  Location:        $Location"
Write-Host ""

# ─── Step 1: Create Resource Group ──────────────────────────────
Write-Host "> Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none

# ─── Step 2: Deploy Infrastructure (Bicep) ─────────────────────
Write-Host "> Deploying infrastructure..." -ForegroundColor Yellow
$deployOutput = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters appName=$AppName postgresAdminPassword=$PostgresPassword `
    --query "properties.outputs" `
    --output json | ConvertFrom-Json

$AcrName = $deployOutput.acrName.value
$AcrLoginServer = $deployOutput.acrLoginServer.value
$WebAppName = $deployOutput.webAppName.value
$WebAppUrl = $deployOutput.webAppUrl.value

Write-Host "  ACR:      $AcrLoginServer"
Write-Host "  Web App:  $WebAppName"

# ─── Step 3: Build & Push Docker Image ─────────────────────────
Write-Host "> Building and pushing Docker image..." -ForegroundColor Yellow
az acr login --name $AcrName

docker build -t "${AcrLoginServer}/${AppName}:latest" .
docker push "${AcrLoginServer}/${AppName}:latest"

# ─── Step 4: Restart Web App ───────────────────────────────────
Write-Host "> Restarting web app..." -ForegroundColor Yellow
az webapp restart --name $WebAppName --resource-group $ResourceGroup

# ─── Done ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "  URL: $WebAppUrl" -ForegroundColor Cyan
Write-Host ""
