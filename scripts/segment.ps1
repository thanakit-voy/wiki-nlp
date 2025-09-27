param(
    [string]$Image = "wiki-nlp-cli",
    [string]$ArticlesDir = "data/articles",
    [string]$Collection = "corpus",
    [int]$Batch = 100,
    [int]$Max = 0,
    [string]$MongoUri = "mongodb://host.docker.internal:27017",
    [string]$MongoDb = "tiktok_live",
    [string]$MongoUser = "appuser",
    [string]$MongoPassword = "apppass",
    [string]$MongoAuthDb = "admin",
    [string]$Network = "",
    [string]$State = "data/state.json"
)

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

$cmd = @(
    "run", "--rm",
    $envs,
    $netArgs,
    "-v", "${PWD}:/app",
    $Image,
    "segment",
    "--articles-dir", $ArticlesDir,
    "--collection", $Collection,
    "--batch", $Batch,
    "--state", $State
)
if ($Max -gt 0) { $cmd += @("--max", $Max) }

Write-Host "docker $($cmd -join ' ')"
docker @cmd
