param(
    [string]$Tag = "wiki-nlp-cli",
    [string]$Name = "world",
    [switch]$Upper
)

$dockerArgs = @("run", "--rm", $Tag, "--", "--name", $Name)
if ($Upper) {
    $dockerArgs += "--upper"
}

Write-Host "Running: docker $($dockerArgs -join ' ')"
docker @dockerArgs
