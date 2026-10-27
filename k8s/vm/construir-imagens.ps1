param([string]$Output = (Join-Path $env:TEMP 'togglemaster-images.tar'))
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')

foreach ($service in @('auth', 'flag', 'targeting', 'evaluation', 'analytics')) {
    docker build -t "localhost/togglemaster-${service}:local" "./Microserviços/${service}-service"
    if ($LASTEXITCODE -ne 0) { throw "Falha no build de $service" }
}
foreach ($image in @('postgres:16-alpine', 'redis:7-alpine', 'amazon/dynamodb-local:latest', 'softwaremill/elasticmq-native:latest')) {
    docker pull $image
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar $image" }
}
docker save -o $Output `
    localhost/togglemaster-auth:local `
    localhost/togglemaster-flag:local `
    localhost/togglemaster-targeting:local `
    localhost/togglemaster-evaluation:local `
    localhost/togglemaster-analytics:local `
    postgres:16-alpine redis:7-alpine `
    amazon/dynamodb-local:latest softwaremill/elasticmq-native:latest
if ($LASTEXITCODE -ne 0) { throw 'Falha ao exportar imagens' }
Write-Host "Imagens salvas em $Output"
