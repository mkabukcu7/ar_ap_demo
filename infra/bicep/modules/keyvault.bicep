// ============================================================
// Module: Azure Key Vault
// ============================================================
targetScope = 'resourceGroup'

param name             string
param location         string
param tags             object
param deployerObjectId string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name:     name
  location: location
  tags:     tags
  properties: {
    sku: {
      family: 'A'
      name:   'standard'
    }
    tenantId:                     subscription().tenantId
    enableRbacAuthorization:      true   // RBAC model; no access policies
    enableSoftDelete:             true
    softDeleteRetentionInDays:    90
    enablePurgeProtection:        true
    publicNetworkAccess:          'Enabled'  // lock down to private endpoint in production
    networkAcls: {
      defaultAction: 'Allow'
      bypass:        'AzureServices'
    }
  }
}

// Grant the deployer Key Vault Administrator so they can seed secrets during CI/CD
resource deployerKvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name:  guid(keyVault.id, deployerObjectId, 'kv-admin')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '00482a5a-887f-4fb3-b363-3b7fe8e74483'   // Key Vault Administrator
    )
    principalId:   deployerObjectId
    principalType: 'User'
  }
}

output keyVaultId   string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri  string = keyVault.properties.vaultUri
