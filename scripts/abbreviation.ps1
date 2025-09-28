param(
  [string]$Image = "wiki-nlp-cli",
  [string]$Collection = "corpus",
  [int]$Limit = 0,
  [int]$Batch = 200,
  [switch]$All,
  [switch]$Verbose,
  [string]$MongoUri = "mongodb://host.docker.internal:27017",
  [string]$MongoDb = "tiktok_live",
  [string]$MongoUser = "appuser",
  [string]$MongoPassword = "apppass",
  [string]$MongoAuthDb = "admin",
  [string]$Network = ""
)

$envs = @(
  "-e", "MONGO_URI=$MongoUri",
  "-e", "MONGO_DB=$MongoDb",
  "-e", "MONGO_USER=$MongoUser",
  "-e", "MONGO_PASSWORD=$MongoPassword",
  "-e", "MONGO_AUTH_DB=$MongoAuthDb",
  "-e", "PYTHONUNBUFFERED=1"
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
  "abbreviation",
  "--collection", $Collection,
  "--batch", $Batch
)

if ($Limit -gt 0) { $cmd += @("--limit", $Limit) }
if ($All) { $cmd += "--all" }
if ($Verbose) { $cmd += "--verbose" }

Write-Host "docker $($cmd -join ' ')"
docker @cmd
