// ============================================================
// Module: RBAC Role Assignments (Managed Identity)
// Assigns least-privilege roles so the backend Container App
// can access Storage, Search, Key Vault, and AI Services
// without any connection strings or keys.
// ============================================================
targetScope = 'resourceGroup'

param backendPrincipalId  string
param storageAccountName  string
param searchServiceName   string
param keyVaultName        string
param docIntelligenceName string

// --------------- Resource references ---------------
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchServiceName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource docIntelligence 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' existing = {
  name: docIntelligenceName
}

// --------------- Role Definitions ---------------
var storageBlobDataContributorId   = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var searchIndexDataContributorId   = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
var searchServiceContributorId     = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
var kvSecretsUserId                = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var cognitiveServicesUserId        = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4dca-a6e2-26227f4b11ca')

// --------------- Storage: Blob Data Contributor ---------------
resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name:  guid(storageAccount.id, backendPrincipalId, storageBlobDataContributorId)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageBlobDataContributorId
    principalId:      backendPrincipalId
    principalType:    'ServicePrincipal'
  }
}

// --------------- Search: Index Data Contributor ---------------
resource searchIndexDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name:  guid(searchService.id, backendPrincipalId, searchIndexDataContributorId)
  scope: searchService
  properties: {
    roleDefinitionId: searchIndexDataContributorId
    principalId:      backendPrincipalId
    principalType:    'ServicePrincipal'
  }
}

// --------------- Search: Service Contributor (for indexer management) ---------------
resource searchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name:  guid(searchService.id, backendPrincipalId, searchServiceContributorId)
  scope: searchService
  properties: {
    roleDefinitionId: searchServiceContributorId
    principalId:      backendPrincipalId
    principalType:    'ServicePrincipal'
  }
}

// --------------- Key Vault: Secrets User ---------------
resource kvSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name:  guid(keyVault.id, backendPrincipalId, kvSecretsUserId)
  scope: keyVault
  properties: {
    roleDefinitionId: kvSecretsUserId
    principalId:      backendPrincipalId
    principalType:    'ServicePrincipal'
  }
}

// --------------- Document Intelligence: Cognitive Services User ---------------
resource cogServicesRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name:  guid(docIntelligence.id, backendPrincipalId, cognitiveServicesUserId)
  scope: docIntelligence
  properties: {
    roleDefinitionId: cognitiveServicesUserId
    principalId:      backendPrincipalId
    principalType:    'ServicePrincipal'
  }
}
