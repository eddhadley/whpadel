// ──────────────────────────────────────────────────────────────
// West Hants Padel Matchmaker – Azure Infrastructure (Bicep)
// Deploys: App Service + PostgreSQL Flexible Server + Container Registry
// ──────────────────────────────────────────────────────────────

targetScope = 'resourceGroup'

// ─── Parameters ────────────────────────────────────────────────

@description('Base name used to derive all resource names (lowercase, no spaces)')
@minLength(3)
@maxLength(20)
param appName string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('PostgreSQL administrator login name')
param postgresAdminUser string = 'padeladmin'

@description('PostgreSQL administrator password')
@secure()
param postgresAdminPassword string

@description('App Service Plan SKU')
@allowed(['B1', 'B2', 'B3', 'S1', 'S2', 'P1v3'])
param appServiceSku string = 'B1'

@description('PostgreSQL Flexible Server SKU')
param postgresSku string = 'Standard_B1ms'

@description('PostgreSQL storage size in GB')
param postgresStorageGB int = 32

@description('SMTP host for sending verification emails (leave empty to skip email config)')
param smtpHost string = ''

@description('SMTP port')
param smtpPort string = '587'

@description('SMTP username')
param smtpUser string = ''

@description('SMTP password or API key')
@secure()
param smtpPassword string = ''

@description('Sender email address for verification emails')
param smtpFrom string = ''

// ─── Variables ─────────────────────────────────────────────────

var uniqueSuffix = uniqueString(resourceGroup().id, appName)
var appServicePlanName = '${appName}-plan'
var webAppName = '${appName}-app'
var acrName = toLower(replace('${appName}acr${take(uniqueSuffix, 4)}', '-', ''))
var postgresServerName = '${appName}-pgserver'
var databaseName = 'padel'
var logAnalyticsName = '${appName}-logs'

// SMTP settings for email verification
var smtpSettings = smtpHost != '' ? [
  {
    name: 'SMTP_HOST'
    value: smtpHost
  }
  {
    name: 'SMTP_PORT'
    value: smtpPort
  }
  {
    name: 'SMTP_USER'
    value: smtpUser
  }
  {
    name: 'SMTP_PASSWORD'
    value: smtpPassword
  }
  {
    name: 'SMTP_FROM'
    value: smtpFrom
  }
] : []

// ─── Log Analytics Workspace ───────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ─── Azure Container Registry ──────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ─── PostgreSQL Flexible Server ────────────────────────────────

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: postgresSku
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: postgresStorageGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Allow Azure services (App Service) to connect to PostgreSQL
resource postgresFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Create the padel database
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ─── App Service Plan (Linux) ──────────────────────────────────

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: appServiceSku
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// ─── Web App (Container) ──────────────────────────────────────

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.properties.loginServer}/${appName}:latest'
      alwaysOn: true
      healthCheckPath: '/api/health'
      appSettings: concat([
        {
          name: 'DATABASE_URL'
          value: 'postgresql://${postgresAdminUser}:${postgresAdminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'
        }
        {
          name: 'PORT'
          value: '8000'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${acr.properties.loginServer}'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: acr.listCredentials().username
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
      ], smtpSettings)
    }
  }
}

// ─── Diagnostics ───────────────────────────────────────────────

resource webAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'AppServiceLogs'
  scope: webApp
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ─── Outputs ───────────────────────────────────────────────────

output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output webAppName string = webApp.name
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output postgresDatabase string = databaseName
