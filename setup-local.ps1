param([switch]$Force)

$ErrorActionPreference = 'Stop'
$envPath = Join-Path $PSScriptRoot '.env'
if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    Write-Host '.env já existe. Use -Force somente se quiser gerar novas credenciais.'
    exit 0
}

function New-HexSecret([int]$byteCount) {
    $bytes = New-Object byte[] $byteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function Get-Sha256Hex([string]$value) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($value))
        return ([BitConverter]::ToString($hash)).Replace('-', '').ToLowerInvariant()
    } finally { $sha.Dispose() }
}

$serviceKey = 'tm_key_' + (New-HexSecret 32)
$content = @(
    'POSTGRES_PASSWORD=' + (New-HexSecret 24)
    'MASTER_KEY=' + (New-HexSecret 32)
    'SERVICE_API_KEY=' + $serviceKey
    'SERVICE_API_KEY_SHA256=' + (Get-Sha256Hex $serviceKey)
)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($envPath, $content, $utf8NoBom)
Write-Host "Credenciais locais gravadas em $envPath"
Write-Host 'Depois execute: docker compose up -d --build'
