// ============================================================
// Module: Log Analytics Workspace + Application Insights
// ============================================================
targetScope = 'resourceGroup'

param workspaceName  string
param appInsightsName string
param location       string
param tags           object

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name:     workspaceName
  location: location
  tags:     tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name:     appInsightsName
  location: location
  tags:     tags
  kind:     'web'
  properties: {
    Application_Type:             'web'
    WorkspaceResourceId:          workspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery:     'Enabled'
  }
}

output workspaceId               string = workspace.id
output workspaceName             string = workspace.name
@secure()
output workspaceKey              string = workspace.listKeys().primarySharedKey
output appInsightsId             string = appInsights.id
output appInsightsName           string = appInsights.name
@secure()
output appInsightsConnectionString   string = appInsights.properties.ConnectionString
