// ============================================================
// Module: Azure AI Search (with semantic ranker)
// ============================================================
targetScope = 'resourceGroup'

param name     string
param location string
param tags     object

@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param sku string = 'standard'

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name:     name
  location: location
  tags:     tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount:              1
    partitionCount:            1
    publicNetworkAccess:       'enabled'    // restrict to private endpoint in production
    disableLocalAuth:          true         // RBAC-only; no admin/query keys used
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'standard'             // enables semantic ranker
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
  }
}

output searchId       string = searchService.id
output searchName     string = searchService.name
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchPrincipalId string = searchService.identity.principalId
