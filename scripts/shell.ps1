param(
    [string]$Image = "wiki-nlp-cli",
    [switch]$Gpu,
    [string]$Shell = "bash",
    [string]$MongoUri = "mongodb://host.docker.internal:27017",
    [string]$MongoDb = "tiktok_live",
    [string]$MongoUser = "appuser",
    [string]$MongoPassword = "apppass",
    [string]$MongoAuthDb = "admin",
    [string]$Network = ""
)

$args = @("run","--rm","-it")
if ($Gpu) { $args += @("--gpus","all") }

$envs = @(
  "-e","MONGO_URI=$MongoUri",
  "-e","MONGO_DB=$MongoDb",
  "-e","MONGO_USER=$MongoUser",
  "-e","MONGO_PASSWORD=$MongoPassword",
  "-e","MONGO_AUTH_DB=$MongoAuthDb"
)

$netArgs = @()
if ($Network -and $Network.Trim() -ne "") { $netArgs = @("--network",$Network) }

$args += $envs
$args += $netArgs
$args += @("-v","${PWD}:/app","-w","/app","--entrypoint",$Shell,$Image)

Write-Host "docker $($args -join ' ')"
docker @args