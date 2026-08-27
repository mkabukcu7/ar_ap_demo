// ============================================================
// Module: Storage Account + Blob Containers
// ============================================================
targetScope = 'resourceGroup'

param name     string
param location string
param tags     object

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name:     name
  location: location
  tags:     tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion:        'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess:    false
    allowSharedKeyAccess:     false  // RBAC-only; no storage keys
    networkAcls: {
      defaultAction: 'Allow'         // tighten to VNet/private endpoint in production
      bypass:        'AzureServices'
    }
    encryption: {
      services: {
        blob: { enabled: true }
        file: { enabled: true }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name:   'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days:    30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days:    30
    }
  }
}

var containers = ['invoices', 'remittances', 'knowledge']

resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [
  for c in containers: {
    parent: blobService
    name:   c
    properties: {
      publicAccess: 'None'
    }
  }
]

output storageId          string = storageAccount.id
output storageAccountName string = storageAccount.name
output blobEndpoint       string = storageAccount.properties.primaryEndpoints.blob
