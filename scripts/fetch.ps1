param(
    [string]$Titles = "data/input/titles.txt",
    [string]$OutDir = "data/articles",
    [string]$State = "data/state.json",
    [string]$Image = "wiki-nlp-cli",
    [string]$Contact = "you@example.com",
    [string]$AppUrl = "https://example.com",
    [int]$Max = 0,
    [double]$Delay = 0.2,
    [double]$Timeout = 15
)

# Ensure base directories exist
New-Item -ItemType Directory -Force -Path (Split-Path $OutDir) | Out-Null
$envArgs = @("-e", "WIKI_CONTACT=$Contact", "-e", "WIKI_APP_URL=$AppUrl")

$cmd = @(
    "run", "--rm",
    $envArgs,
    "-v", "${PWD}:/app",
    $Image,
    "fetch",
    "--titles", $Titles,
    "--out-dir", $OutDir,
    "--state", $State,
    "--delay", $Delay,
    "--timeout", $Timeout
) | ForEach-Object { $_ } # flatten

if ($Max -gt 0) { $cmd += @("--max", $Max) }

Write-Host "docker $($cmd -join ' ')"
docker @cmd
