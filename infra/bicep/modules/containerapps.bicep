// ============================================================
// Module: Azure Container Apps Environment + Backend + Frontend
// ============================================================
targetScope = 'resourceGroup'

param envName          string
param backendAppName   string
param frontendAppName  string
param location         string
param tags             object
param logAnalyticsWorkspaceId string
@secure()
param logAnalyticsKey         string
param backendImage            string
param frontendImage           string
param aiProjectEndpoint       string
param searchEndpoint          string
param searchIndex             string
param storageAccountName      string
@secure()
param appInsightsConnectionString string

// --------------- Container Apps Environment ---------------
resource caEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name:     envName
  location: location
  tags:     tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspaceId
        sharedKey:  logAnalyticsKey
      }
    }
    zoneRedundant: false
  }
}

// --------------- Backend (FastAPI) ---------------
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name:     backendAppName
  location: location
  tags:     tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: {
        external:   true
        targetPort: 8000
        transport:  'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name:  'api'
          image: backendImage
          resources: {
            cpu:    '0.5'
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_AI_PROJECT_ENDPOINT',          value: aiProjectEndpoint }
            { name: 'AZURE_AI_MODEL_DEPLOYMENT',          value: 'gpt-5.4' }
            { name: 'AZURE_SEARCH_ENDPOINT',              value: searchEndpoint }
            { name: 'AZURE_SEARCH_INDEX',                 value: searchIndex }
            { name: 'AZURE_STORAGE_ACCOUNT',              value: storageAccountName }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'FINANCE_AGENT_MODE',                 value: 'foundry' }
            { name: 'FINANCE_CORS_ORIGINS',               value: 'https://${frontendAppName}.${caEnv.properties.defaultDomain}' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

// --------------- Frontend (React) ---------------
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name:     frontendAppName
  location: location
  tags:     tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: {
        external:   true
        targetPort: 3000
        transport:  'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name:  'ui'
          image: frontendImage
          resources: {
            cpu:    '0.25'
            memory: '0.5Gi'
          }
          env: [
            { name: 'API_BASE_URL', value: 'https://${backendApp.properties.configuration.ingress.fqdn}' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output backendUrl          string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl         string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output backendPrincipalId  string = backendApp.identity.principalId
output frontendPrincipalId string = frontendApp.identity.principalId
output caEnvId             string = caEnv.id
