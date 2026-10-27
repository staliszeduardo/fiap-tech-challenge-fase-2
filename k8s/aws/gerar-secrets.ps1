param(
    [string]$RdsHost = 'rds-fiap.c8lau8o86dle.us-east-1.rds.amazonaws.com',
    [string]$RdsUser = 'postgres',
    [Security.SecureString]$DatabasePassword,
    [string]$OutputDirectory = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$outputFile = Join-Path $OutputDirectory '03-secrets.yaml'
if (Test-Path -LiteralPath $outputFile) {
    throw '03-secrets.yaml ja existe. Reutilize-o; nao gere novas chaves sem planejar a atualizacao dos Pods e do RDS.'
}
if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    throw 'A pasta de destino precisa existir.'
}
if (-not $DatabasePassword) {
    $DatabasePassword = Read-Host 'Senha ATUAL do usuario do RDS (nao sera alterada)' -AsSecureString
}

function New-HexSecret([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function ConvertTo-Base64([string]$Value) {
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value))
}

$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($DatabasePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    if ([string]::IsNullOrEmpty($plainPassword)) { throw 'A senha do RDS nao pode estar vazia.' }
    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $encodedUser = [Uri]::EscapeDataString($RdsUser)
    $serviceKey = 'tm_key_' + (New-HexSecret 32)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $serviceHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($serviceKey)))).Replace('-', '').ToLowerInvariant()
    } finally { $sha.Dispose() }
    $values = [ordered]@{
        RDS_HOST = $RdsHost
        RDS_USER = $RdsUser
        POSTGRES_PASSWORD = $plainPassword
        MASTER_KEY = (New-HexSecret 32)
        SERVICE_API_KEY = $serviceKey
        SERVICE_API_KEY_SHA256 = $serviceHash
        AUTH_DATABASE_URL = "postgresql://${encodedUser}:${encodedPassword}@${RdsHost}:5432/authdb?sslmode=require"
        FLAG_DATABASE_URL = "postgresql://${encodedUser}:${encodedPassword}@${RdsHost}:5432/flagdb?sslmode=require"
        TARGETING_DATABASE_URL = "postgresql://${encodedUser}:${encodedPassword}@${RdsHost}:5432/targetingdb?sslmode=require"
    }
    $lines = @(
        '# Gerado localmente. Contem credenciais codificadas em base64; nao publique este arquivo.'
        'apiVersion: v1'
        'kind: Secret'
        'metadata:'
        '  name: togglemaster-secrets'
        '  namespace: togglemaster'
        'type: Opaque'
        'data:'
    )
    foreach ($key in $values.Keys) { $lines += ('  {0}: {1}' -f $key, (ConvertTo-Base64 $values[$key])) }
    [IO.File]::WriteAllLines($outputFile, $lines, [Text.UTF8Encoding]::new($false))
    Write-Host "Secret gerado em $outputFile. A senha do RDS foi reutilizada; nenhuma chamada a AWS foi executada."
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    $plainPassword = $null
    $encodedPassword = $null
    $values = $null
}
