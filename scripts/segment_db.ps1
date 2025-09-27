param(
    [string]$Image = "wiki-nlp-cli",
    [string]$ArticlesDir = "data/output/articles",
    [string]$Collection = "corpus",
    [int]$Batch = 100,
    [int]$Max = 0,
    [string]$MongoUri = "mongodb://localhost:27017",
    [string]$MongoDb = "tiktok_live",
    [string]$MongoUser = "appuser",
    [string]$MongoPassword = "apppass",
    [string]$MongoAuthDb = "admin"
)

$envs = @(
    "-e", "MONGO_URI=$MongoUri",
    "-e", "MONGO_DB=$MongoDb",
    "-e", "MONGO_USER=$MongoUser",
    "-e", "MONGO_PASSWORD=$MongoPassword",
    "-e", "MONGO_AUTH_DB=$MongoAuthDb"
)

$cmd = @(
    "run", "--rm",
    $envs,
    "-v", "${PWD}:/app",
    $Image,
    "segment-db",
    "--articles-dir", $ArticlesDir,
    "--collection", $Collection,
    "--batch", $Batch
)
if ($Max -gt 0) { $cmd += @("--max", $Max) }

Write-Host "docker $($cmd -join ' ')"
docker @cmd