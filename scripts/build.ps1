param(
    [string]$Tag = "wiki-nlp-cli"
)

Write-Host "Building Docker image: $Tag"
docker build -t $Tag .
