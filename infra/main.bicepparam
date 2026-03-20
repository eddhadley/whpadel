using 'main.bicep'

param appName = 'whpadel'
param postgresAdminUser = 'padeladmin'
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_PASSWORD', '')
param appServiceSku = 'B1'
param postgresSku = 'Standard_B1ms'
param postgresStorageGB = 32

// Email verification SMTP settings (optional - leave empty for console-only dev mode)
param smtpHost = readEnvironmentVariable('SMTP_HOST', '')
param smtpPort = '587'
param smtpUser = readEnvironmentVariable('SMTP_USER', '')
param smtpPassword = readEnvironmentVariable('SMTP_PASSWORD', '')
param smtpFrom = readEnvironmentVariable('SMTP_FROM', 'noreply@westhants-padel.com')
