// ============================================================
// Module: Azure AI Foundry Hub + Project + gpt-5.4 Deployment
// ============================================================
targetScope = 'resourceGroup'

param hubName            string
param projectName        string
param location           string
param tags               object
param storageAccountId   string
param keyVaultId         string
param appInsightsId      string
param searchServiceId    string
param modelDeploymentName string
param modelName           string
param modelCapacity       int

// --------------- AI Hub (MachineLearning Workspace kind=Hub) ---------------
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name:     hubName
  location: location
  tags:     tags
  kind:     'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName:      'Finance Operations AI Hub'
    description:       'AI Foundry hub for Finance Operations Agent Accelerator'
    storageAccount:    storageAccountId
    keyVault:          keyVaultId
    applicationInsights: appInsightsId
    publicNetworkAccess: 'Enabled'   // restrict to private endpoint in production
  }
}

// --------------- AI Project ---------------
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name:     projectName
  location: location
  tags:     tags
  kind:     'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Finance Operations Project'
    description:  'AP/AR/Finance Knowledge agent project'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
}

// --------------- gpt-5.4 Model Deployment via AI Services account ---------------
// The Foundry hub creates an underlying CognitiveServices/accounts resource.
// We reference it by convention and deploy the model there.
resource foundryAIServices 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name:     '${hubName}-ai'
  location: location
  tags:     tags
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: '${hubName}-ai'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth:    true
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: foundryAIServices
  name:   modelDeploymentName
  sku: {
    name:     'GlobalStandard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format:  'OpenAI'
      name:    modelName
      version: '2025-01-01'  // use latest available; update as needed
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

// --------------- Azure AI Search connection on Hub ---------------
resource searchConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' = {
  parent: aiHub
  name:   'search-connection'
  properties: {
    category:   'CognitiveSearch'
    target:     'https://${last(split(searchServiceId, '/'))}.search.windows.net'
    authType:   'ManagedIdentity'
    isSharedToAll: true
  }
}

output hubId            string = aiHub.id
output projectId        string = aiProject.id
output projectEndpoint  string = 'https://${aiProject.properties.discoveryUrl ?? '${location}.api.azureml.ms'}/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.MachineLearningServices/workspaces/${projectName}'
output aiServicesId     string = foundryAIServices.id
output aiServicesEndpoint string = foundryAIServices.properties.endpoint
output modelDeploymentName string = modelDeployment.name
output hubPrincipalId   string = aiHub.identity.principalId
output projectPrincipalId string = aiProject.identity.principalId
