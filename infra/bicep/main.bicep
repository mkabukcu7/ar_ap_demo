// ============================================================
// Finance Operations Agent Accelerator — Main Bicep Template
// Scope: Resource Group
// Deploy with:
//   az deployment group create \
//     --resource-group <rg-name> \
//     --template-file infra/bicep/main.bicep \
//     --parameters @infra/bicep/main.parameters.json
// ============================================================
targetScope = 'resourceGroup'

// --------------- Parameters ---------------
@description('Short environment label, e.g. dev | staging | prod.')
param environmentName string = 'dev'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('GPT model deployment name (must match model name).')
param modelDeploymentName string = 'gpt-5.4'

@description('GPT model name.')
param modelName string = 'gpt-5.4'

@description('Capacity units for the model deployment (TPM × 1000).')
param modelCapacity int = 10

@description('Azure Container Registry image for the backend API.')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Azure Container Registry image for the frontend UI.')
param frontendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Object ID of the deploying principal (for initial Key Vault access).')
param deployerObjectId string = ''

// --------------- Variables ---------------
var suffix          = uniqueString(resourceGroup().id)
var abbrev          = take(replace(environmentName, '-', ''), 8)
var namePrefix      = 'fin${abbrev}${take(suffix, 6)}'
var tags = {
  environment: environmentName
  application: 'finance-operations-agent-accelerator'
  managedBy:   'bicep'
}

// --------------- Modules ---------------
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name:     'st${namePrefix}'
    location: location
    tags:     tags
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  params: {
    name:     'srch-${namePrefix}'
    location: location
    tags:     tags
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    name:             'kv-${take(namePrefix, 16)}'
    location:         location
    tags:             tags
    deployerObjectId: deployerObjectId
  }
}

module logAnalytics 'modules/loganalytics.bicep' = {
  name: 'logAnalytics'
  params: {
    workspaceName:  'law-${namePrefix}'
    appInsightsName:'appi-${namePrefix}'
    location:       location
    tags:           tags
  }
}

module docIntelligence 'modules/documentintelligence.bicep' = {
  name: 'docIntelligence'
  params: {
    name:     'di-${namePrefix}'
    location: location
    tags:     tags
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    hubName:             'aih-${namePrefix}'
    projectName:         'aip-${namePrefix}'
    location:            location
    tags:                tags
    storageAccountId:    storage.outputs.storageId
    keyVaultId:          keyVault.outputs.keyVaultId
    appInsightsId:       logAnalytics.outputs.appInsightsId
    searchServiceId:     search.outputs.searchId
    modelDeploymentName: modelDeploymentName
    modelName:           modelName
    modelCapacity:       modelCapacity
  }
}

module containerApps 'modules/containerapps.bicep' = {
  name: 'containerApps'
  params: {
    envName:              'cae-${namePrefix}'
    backendAppName:       'ca-api-${namePrefix}'
    frontendAppName:      'ca-ui-${namePrefix}'
    location:             location
    tags:                 tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    logAnalyticsKey:         logAnalytics.outputs.workspaceKey
    backendImage:            backendImage
    frontendImage:           frontendImage
    aiProjectEndpoint:       foundry.outputs.projectEndpoint
    searchEndpoint:          search.outputs.searchEndpoint
    searchIndex:             'finance-knowledge'
    storageAccountName:      storage.outputs.storageAccountName
    appInsightsConnectionString: logAnalytics.outputs.appInsightsConnectionString
  }
}

module roleAssignments 'modules/roleassignments.bicep' = {
  name: 'roleAssignments'
  params: {
    backendPrincipalId:  containerApps.outputs.backendPrincipalId
    storageAccountName:  storage.outputs.storageAccountName
    searchServiceName:   search.outputs.searchName
    keyVaultName:        keyVault.outputs.keyVaultName
    docIntelligenceName: docIntelligence.outputs.docIntelligenceName
  }
}

// --------------- Outputs ---------------
output projectEndpoint           string = foundry.outputs.projectEndpoint
output searchEndpoint            string = search.outputs.searchEndpoint
output storageAccountName        string = storage.outputs.storageAccountName
output appInsightsConnectionString string = logAnalytics.outputs.appInsightsConnectionString
output backendUrl                string = containerApps.outputs.backendUrl
output frontendUrl               string = containerApps.outputs.frontendUrl
output keyVaultName              string = keyVault.outputs.keyVaultName
