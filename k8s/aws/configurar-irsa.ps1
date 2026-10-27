param(
    [string]$ClusterName = 'fiap-techchallenge',
    [string]$Region = 'us-east-1'
)

$ErrorActionPreference = 'Stop'
$expectedAccount = '608541039538'

function Invoke-AwsJson([string[]]$CliArguments) {
    $commandOutput = & aws @CliArguments --output json --no-cli-pager
    if ($LASTEXITCODE -ne 0) { throw "Falha na chamada AWS: $($CliArguments[0]) $($CliArguments[1])." }
    if ($commandOutput) { return ($commandOutput | Out-String | ConvertFrom-Json) }
}

$identity = Invoke-AwsJson -CliArguments @('sts', 'get-caller-identity', '--region', $Region)
if ($identity.Account -ne $expectedAccount) { throw "Use a conta AWS $expectedAccount. Conta atual: $($identity.Account)." }
$cluster = Invoke-AwsJson -CliArguments @('eks', 'describe-cluster', '--name', $ClusterName, '--region', $Region)
if ($cluster.cluster.status -ne 'ACTIVE') { throw 'O cluster precisa estar ACTIVE.' }
$issuer = $cluster.cluster.identity.oidc.issuer -replace '^https://', ''
if (-not $issuer) { throw 'O cluster nao retornou um emissor OIDC.' }
$providerArn = "arn:aws:iam::${expectedAccount}:oidc-provider/$issuer"
$null = Invoke-AwsJson -CliArguments @('iam', 'get-open-id-connect-provider', '--open-id-connect-provider-arn', $providerArn)

$settings = @(
    @{ ServiceAccount = 'evaluation-service'; Role = 'ToggleMasterEvaluationRole'; PolicyFile = 'evaluation-policy.json' }
    @{ ServiceAccount = 'analytics-service'; Role = 'ToggleMasterAnalyticsRole'; PolicyFile = 'analytics-policy.json' }
)
foreach ($setting in $settings) {
    $roleName = $setting.Role
    $conditions = @{}
    $conditions["${issuer}:aud"] = 'sts.amazonaws.com'
    $conditions["${issuer}:sub"] = "system:serviceaccount:togglemaster:$($setting.ServiceAccount)"
    $trust = @{
        Version = '2012-10-17'
        Statement = @(@{
            Effect = 'Allow'
            Principal = @{ Federated = $providerArn }
            Action = 'sts:AssumeRoleWithWebIdentity'
            Condition = @{ StringEquals = $conditions }
        })
    }
    $trustFile = Join-Path ([IO.Path]::GetTempPath()) (('togglemaster-trust-' + [Guid]::NewGuid().ToString('N')) + '.json')
    try {
        [IO.File]::WriteAllText($trustFile, ($trust | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
        $existing = @(Invoke-AwsJson -CliArguments @('iam', 'list-roles', '--query', "Roles[?RoleName=='$roleName']"))
        if ($existing.Count -gt 0) {
            $tagResult = Invoke-AwsJson -CliArguments @('iam', 'list-role-tags', '--role-name', $roleName)
            $ownerTags = @($tagResult.Tags | Where-Object { $_.Key -eq 'ManagedBy' -and $_.Value -eq 'togglemaster-k8s-aws' })
            $stackTags = @($tagResult.Tags | Where-Object { $_.Key -eq 'aws:cloudformation:stack-name' })
            if ($ownerTags.Count -ne 1 -or $stackTags.Count -gt 0) {
                throw "A role $roleName ja existe e pertence a outra configuracao. Ela nao foi alterada."
            }
            $null = Invoke-AwsJson -CliArguments @('iam', 'update-assume-role-policy', '--role-name', $roleName, '--policy-document', "file://$trustFile")
        } else {
            $null = Invoke-AwsJson -CliArguments @('iam', 'create-role', '--role-name', $roleName, '--assume-role-policy-document', "file://$trustFile", '--tags', 'Key=Project,Value=ToggleMaster', 'Key=ManagedBy,Value=togglemaster-k8s-aws')
        }
        $policyFile = Join-Path (Join-Path $PSScriptRoot 'iam') $setting.PolicyFile
        $null = Invoke-AwsJson -CliArguments @('iam', 'put-role-policy', '--role-name', $roleName, '--policy-name', 'ToggleMasterApplicationAccess', '--policy-document', "file://$policyFile")
        Write-Host "IRSA preparado: $roleName -> togglemaster/$($setting.ServiceAccount)"
    } finally {
        if ([IO.File]::Exists($trustFile)) { [IO.File]::Delete($trustFile) }
    }
}
Write-Host 'Aguardando 15 segundos para propagacao do IAM...'
Start-Sleep -Seconds 15
Write-Host 'Agora aplique 04-serviceaccounts.yaml, antes de criar os Pods das aplicacoes.'
