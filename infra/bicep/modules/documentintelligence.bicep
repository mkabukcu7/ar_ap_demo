// ============================================================
// Module: Azure AI Services (Document Intelligence)
// ============================================================
targetScope = 'resourceGroup'

param name     string
param location string
param tags     object

resource docIntelligence 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name:     name
  location: location
  tags:     tags
  sku: {
    name: 'S0'
  }
  kind: 'FormRecognizer'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName:    name
    publicNetworkAccess:    'Enabled'
    disableLocalAuth:       true        // RBAC-only; no subscription keys used
    networkAcls: {
      defaultAction: 'Allow'
      bypass:        'AzureServices'
    }
  }
}

output docIntelligenceId        string = docIntelligence.id
output docIntelligenceName      string = docIntelligence.name
output docIntelligenceEndpoint  string = docIntelligence.properties.endpoint
output docIntelligencePrincipalId string = docIntelligence.identity.principalId
