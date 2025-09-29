param(
    [string]$Tag = "wiki-nlp-cli",
    [string]$Collection = "corpus",
    [switch]$All,
    [switch]$Train = $true,
    [int]$Limit = 100,
    [int]$EncodeBatch = 64,
    [int]$TrainEpochs = 1,
    [int]$TrainBatch = 64,
    [int]$TrainLimitDocs = 10,
    [switch]$Gpu,
    [string]$MongoUri = "mongodb://host.docker.internal:27017",
    [string]$MongoDb = "tiktok_live",
    [string]$MongoUser = "appuser",
    [string]$MongoPassword = "apppass",
    [string]$MongoAuthDb = "admin",
    [string]$Network = "",
    [switch]$Verbose
)

$dockerArgs = @("run", "--rm")
if ($Gpu) { $dockerArgs += @("--gpus", "all") }

$envs = @(
    "-e", "MONGO_URI=$MongoUri",
    "-e", "MONGO_DB=$MongoDb",
    "-e", "MONGO_USER=$MongoUser",
    "-e", "MONGO_PASSWORD=$MongoPassword",
    "-e", "MONGO_AUTH_DB=$MongoAuthDb"
)

$netArgs = @()
if ($Network -and $Network.Trim() -ne "") {
    $netArgs = @("--network", $Network)
}

$dockerArgs += @($envs)
$dockerArgs += @($netArgs)
$dockerArgs += @("-v", "${PWD}:/app")
$dockerArgs += @($Tag, "embeddings", "--collection", $Collection, "--encode-batch", "$EncodeBatch")

if ($Limit -gt 0) { $dockerArgs += @("--limit", "$Limit") }
if ($All) { $dockerArgs += "--all" }
if ($Train) {
    $dockerArgs += @("--train", "--train-epochs", "$TrainEpochs", "--train-batch", "$TrainBatch")
    if ($TrainLimitDocs -gt 0) { $dockerArgs += @("--train-limit-docs", "$TrainLimitDocs") }
}
if ($Verbose) { $dockerArgs += "--verbose" }

Write-Host "Running: docker $($dockerArgs -join ' ')"
docker @dockerArgs
