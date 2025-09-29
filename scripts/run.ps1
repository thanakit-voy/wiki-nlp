param(
    [string]$Tag = "wiki-nlp-cli",
    [string]$Name = "world",
    [switch]$Upper,
    [switch]$Gpu,
    [string]$MongoUri = "mongodb://host.docker.internal:27017",
    [string]$MongoDb = ""
)

$dockerArgs = @("run", "--rm")
if ($Gpu) { $dockerArgs += @("--gpus", "all") }
if ($MongoUri -ne "") { $dockerArgs += @("-e", "MONGO_URI=$MongoUri") }
if ($MongoDb -ne "") { $dockerArgs += @("-e", "MONGO_DB=$MongoDb") }

$dockerArgs += @($Tag, "--name", $Name)
if ($Upper) { $dockerArgs += "--upper" }

Write-Host "Running: docker $($dockerArgs -join ' ')"
docker @dockerArgs
