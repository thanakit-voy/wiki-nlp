<#!
.SYNOPSIS
Runs the wiki-nlp processing pipeline in batches until completion.

.DESCRIPTION
This script orchestrates the following steps and repeats each until the stop condition is met:
  (optional) .\scripts\fetch.ps1 -Max 100   -> enabled with -Fetch; until no additional logs are produced (quiet)
  (optional) .\scripts\segment.ps1          -> enabled with -Segment; until no additional logs are produced (quiet)
  3) .\scripts\thai_clock.ps1              -> until log contains "modified documents: 0"
  4) .\scripts\sentences.ps1               -> until log contains "modified documents: 0"
  5) .\scripts\sentence_token.ps1          -> until log contains "modified documents: 0"
  6) .\scripts\tag_num.ps1                 -> until log contains "modified documents: 0"
  7) .\scripts\connectors.ps1              -> until log contains "modified documents: 0"
  8) .\scripts\abbreviation.ps1            -> until log contains "modified documents: 0"
  9) .\scripts\tokenize.ps1                -> until log contains "modified documents: 0"
  10) .\scripts\sentence_heads.ps1         -> until log contains "modified documents: 0"

By default, a short sleep is applied between iterations to avoid tight loops.

.PARAMETER MaxIterations
Safety cap for maximum iterations per step. Defaults to 1000.

.PARAMETER SleepSeconds
Delay between iterations of a step. Defaults to 1 second.

.PARAMETER Fetch
When provided, runs the fetch step before others.

.PARAMETER Segment
When provided, runs the segment step before others.

.EXAMPLE
PS> .\scripts\pipeline.ps1

Runs all steps until completion with defaults.

.EXAMPLE
PS> .\scripts\pipeline.ps1 -MaxIterations 200 -SleepSeconds 2

Adjusts safety caps and sleep between iterations.
#>

param(
  [int]$MaxIterations = 1000,
  [int]$SleepSeconds = 1,
  [switch]$Fetch,
  [switch]$Segment
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-StepUntilQuiet {
  param(
    [Parameter(Mandatory)] [scriptblock] $Invoker,
    [string] $StepName = ""
  )

  for ($i = 1; $i -le $MaxIterations; $i++) {
    Write-Host "==== [$StepName] Iteration $i ====" -ForegroundColor Cyan
    # Avoid treating stderr from native commands (e.g., docker) as terminating errors
    $origEAP = $ErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      $out = & $Invoker 2>&1 | Tee-Object -Variable _tmp
    }
    finally {
      $ErrorActionPreference = $origEAP
    }
    # Consider output "quiet" when there are no non-empty lines other than the echoed docker line(s)
    $payload = $out | Where-Object { $_ -and ($_ -notmatch '^\s*$') -and ($_ -notmatch '^\s*docker\s') }
    if (($payload | Measure-Object).Count -eq 0) {
      Write-Host "[$StepName] No additional logs detected -> done." -ForegroundColor Green
      break
    }
    Start-Sleep -Seconds $SleepSeconds
    if ($i -eq $MaxIterations) {
      Write-Warning "[$StepName] Reached MaxIterations ($MaxIterations) without becoming quiet."
    }
  }
}

function Invoke-StepUntilMatch {
  param(
    [Parameter(Mandatory)] [scriptblock] $Invoker,
    [string] $StepName = "",
    [string] $Pattern = 'modified\s+documents:\s*0',
    [string] $DoneMessage = "matched pattern"
  )

  for ($i = 1; $i -le $MaxIterations; $i++) {
    Write-Host "==== [$StepName] Iteration $i ====" -ForegroundColor Cyan
    # Avoid treating stderr from native commands (e.g., docker) as terminating errors
    $origEAP = $ErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      $out = & $Invoker 2>&1 | Tee-Object -Variable _tmp
    }
    finally {
      $ErrorActionPreference = $origEAP
    }
    $text = ($out -join "`n")
    if ($text -match $Pattern) {
      Write-Host "[$StepName] $DoneMessage -> done." -ForegroundColor Green
      break
    }
    Start-Sleep -Seconds $SleepSeconds
    if ($i -eq $MaxIterations) {
      Write-Warning "[$StepName] Reached MaxIterations ($MaxIterations) without seeing pattern: $Pattern"
    }
  }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$fetchScript     = Join-Path $scriptRoot 'fetch.ps1'
$segmentScript   = Join-Path $scriptRoot 'segment.ps1'
$thaiClockScript = Join-Path $scriptRoot 'thai_clock.ps1'
$sentencesScript = Join-Path $scriptRoot 'sentences.ps1'
${sentenceTokenScript} = Join-Path $scriptRoot 'sentence_token.ps1'
${tagNumScript}       = Join-Path $scriptRoot 'tag_num.ps1'
${connectorsScript}   = Join-Path $scriptRoot 'connectors.ps1'
${abbreviationScript} = Join-Path $scriptRoot 'abbreviation.ps1'
${tokenizeScript}     = Join-Path $scriptRoot 'tokenize.ps1'
${sentenceHeadsScript} = Join-Path $scriptRoot 'sentence_heads.ps1'

if (-not (Test-Path $fetchScript))     { throw "Missing script: $fetchScript" }
if (-not (Test-Path $segmentScript))   { throw "Missing script: $segmentScript" }
if (-not (Test-Path $thaiClockScript)) { throw "Missing script: $thaiClockScript" }
if (-not (Test-Path $sentencesScript)) { throw "Missing script: $sentencesScript" }
if (-not (Test-Path $sentenceTokenScript)) { throw "Missing script: $sentenceTokenScript" }
if (-not (Test-Path $tagNumScript))       { throw "Missing script: $tagNumScript" }
if (-not (Test-Path $connectorsScript))   { throw "Missing script: $connectorsScript" }
if (-not (Test-Path $abbreviationScript)) { throw "Missing script: $abbreviationScript" }
if (-not (Test-Path $tokenizeScript))     { throw "Missing script: $tokenizeScript" }
if (-not (Test-Path $sentenceHeadsScript)) { throw "Missing script: $sentenceHeadsScript" }

# (optional) fetch.ps1 -Max 100 until quiet
if ($Fetch) { Invoke-StepUntilQuiet -StepName 'fetch' -Invoker { & $fetchScript -Max 100 } } else { Write-Host "Skipping fetch (no -Fetch)." -ForegroundColor Yellow }

# (optional) segment.ps1 until quiet
if ($Segment) { Invoke-StepUntilQuiet -StepName 'segment' -Invoker { & $segmentScript } } else { Write-Host "Skipping segment (no -Segment)." -ForegroundColor Yellow }

# Reorder steps by moving these single lines
# 3) thai_clock.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'thai_clock' -Invoker { & $thaiClockScript }

# 4) sentences.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'sentences' -Invoker { & $sentencesScript }

# 5) sentence_token.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'sentence_token' -Invoker { & $sentenceTokenScript }

# 6) tag_num.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'tag_num' -Invoker { & $tagNumScript }

# 7) connectors.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'connectors' -Invoker { & $connectorsScript }

# 8) abbreviation.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'abbreviation' -Invoker { & $abbreviationScript }

# 9) tokenize.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'tokenize' -Invoker { & $tokenizeScript }

# 10) sentence_heads.ps1 until "modified documents: 0"
Invoke-StepUntilMatch -StepName 'sentence_heads' -Invoker { & $sentenceHeadsScript }

Write-Host "All steps completed." -ForegroundColor Green
