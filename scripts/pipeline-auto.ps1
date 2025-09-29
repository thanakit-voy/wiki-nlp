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
  11) .\scripts\word_pattern.ps1           -> until log contains "modified documents: 0"

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

# === Load limits.jsonl as hashtable ===
$limitsPath = Join-Path $scriptRoot '..' 'limits.jsonl'
$limitsTable = @{}
if (Test-Path $limitsPath) {
  Get-Content $limitsPath | ForEach-Object {
    if ($_ -match '\S') {
      $obj = $_ | ConvertFrom-Json
      $limitsTable[$obj.script] = $obj.limit
    }
  }
}
$limitsTableNew = @{}

# Record pipeline start time
$__pipelineStart = Get-Date
function Get-LimitForScript {
  param([string]$ScriptName)
  if ($limitsTable.ContainsKey($ScriptName)) {
    return $limitsTable[$ScriptName]
  } else {
    return $null
  }
}

# === Step runner with limit and auto-tune ===

# Step runner with limit (or not) and auto-tune
function Invoke-StepWithLimit {
  param(
    [Parameter(Mandatory)] [string] $ScriptPath,
    [string] $StepName,
    [string] $Pattern = 'modified\\s+documents:\\s*0',
    [string] $DoneMessage = 'matched pattern',
    [int] $MaxIterations = 1000,
    [string] $LimitParamName = 'Limit'  # 'Limit' or 'Max'
  )
  $scriptFile = Split-Path $ScriptPath -Leaf
  $limit = Get-LimitForScript $scriptFile
  $autoLimit = $limit
  $iterationStats = @()
  for ($i = 1; $i -le $MaxIterations; $i++) {
    $now = Get-Date -Format 'HH:mm:ss'
    $elapsed = (New-TimeSpan -Start $__pipelineStart -End (Get-Date))
    $elapsedStr = "{0:D2}:{1:D2}:{2:D2}" -f $elapsed.Hours, $elapsed.Minutes, $elapsed.Seconds
    Write-Host ("==== [$StepName] Iteration $i [{0}] (+{1}) ====" -f $now, $elapsedStr) -ForegroundColor Cyan
    $origEAP = $ErrorActionPreference
    $startTime = Get-Date
    try {
      $ErrorActionPreference = 'Continue'
      if ($null -ne $autoLimit) {
        if ($LimitParamName -eq 'Max') {
          $out = & $ScriptPath -Max $autoLimit 2>&1 | Tee-Object -Variable _tmp
        } else {
          $out = & $ScriptPath -Limit $autoLimit 2>&1 | Tee-Object -Variable _tmp
        }
      } else {
        $out = & $ScriptPath 2>&1 | Tee-Object -Variable _tmp
      }
    } finally {
      $ErrorActionPreference = $origEAP
    }
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    $iterationStats += $duration
    if ($null -ne $autoLimit) {
      Write-Host ("[$StepName] Iteration $i duration: {0:N1} sec ({1}={2})" -f $duration, $LimitParamName, $autoLimit) -ForegroundColor Yellow
    } else {
      Write-Host ("[$StepName] Iteration $i duration: {0:N1} sec (default limit)" -f $duration) -ForegroundColor Yellow
    }
    $text = ($out -join "`n")
    if ($text -match $Pattern) {
      Write-Host "[$StepName] $DoneMessage -> done." -ForegroundColor Green
      break
    }
    # Auto-tune limit for next iteration (from 2nd round onwards)
    if ($null -ne $autoLimit -and $i -ge 2 -and $duration -lt 300) {
      $prevDuration = $iterationStats[$i-2]
      if ($prevDuration -gt 0) {
        $factor = [math]::Ceiling(300 / [math]::Max($duration,1))
        $autoLimit = [math]::Max([int]($autoLimit * $factor), $autoLimit+1)
        Write-Host ("[$StepName] Auto-tune: new {0} for next round = {1}" -f $LimitParamName, $autoLimit) -ForegroundColor Magenta
      }
    }
    Start-Sleep -Seconds $SleepSeconds
    if ($i -eq $MaxIterations) {
      Write-Warning "[$StepName] Reached MaxIterations ($MaxIterations) without seeing pattern: $Pattern"
    }
  }
  # Save last used limit for this script (only if we used a limit)
  if ($null -ne $autoLimit) {
    $limitsTableNew[$scriptFile] = $autoLimit
  }
}

function Invoke-StepUntilQuiet {
  param(
    [Parameter(Mandatory)] [scriptblock] $Invoker,
    [string] $StepName = ""
  )

  for ($i = 1; $i -le $MaxIterations; $i++) {
    $now = Get-Date -Format 'HH:mm'
    $elapsed = (New-TimeSpan -Start $__pipelineStart -End (Get-Date))
    $elapsedStr = "{0:D2}:{1:D2}" -f $elapsed.Hours, $elapsed.Minutes
    Write-Host ("==== [$StepName] Iteration $i [{0}] (+{1}) ====" -f $now, $elapsedStr) -ForegroundColor Cyan
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
    $now = Get-Date -Format 'HH:mm'
    $elapsed = (New-TimeSpan -Start $__pipelineStart -End (Get-Date))
    $elapsedStr = "{0:D2}:{1:D2}" -f $elapsed.Hours, $elapsed.Minutes
    Write-Host ("==== [$StepName] Iteration $i [{0}] (+{1}) ====" -f $now, $elapsedStr) -ForegroundColor Cyan
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
${wordPatternScript}   = Join-Path $scriptRoot 'word_pattern.ps1'

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
if (-not (Test-Path $wordPatternScript))   { throw "Missing script: $wordPatternScript" }


# (optional) fetch.ps1 -Max [auto] until quiet
if ($Fetch) {
  $fetchLimit = Get-LimitForScript (Split-Path $fetchScript -Leaf)
  if ($null -ne $fetchLimit) {
    Invoke-StepWithLimit -ScriptPath $fetchScript -StepName 'fetch' -Pattern '' -DoneMessage 'quiet' -LimitParamName 'Max'
  } else {
    Invoke-StepUntilQuiet -StepName 'fetch' -Invoker { & $fetchScript }
  }
} else { Write-Host "Skipping fetch (no -Fetch)." -ForegroundColor Yellow }

# (optional) segment.ps1 -Max [auto] until quiet
if ($Segment) {
  $segmentLimit = Get-LimitForScript (Split-Path $segmentScript -Leaf)
  if ($null -ne $segmentLimit) {
    Invoke-StepWithLimit -ScriptPath $segmentScript -StepName 'segment' -Pattern '' -DoneMessage 'quiet' -LimitParamName 'Max'
  } else {
    Invoke-StepUntilQuiet -StepName 'segment' -Invoker { & $segmentScript }
  }
} else { Write-Host "Skipping segment (no -Segment)." -ForegroundColor Yellow }

# Reorder steps by moving these single lines


# 3) thai_clock.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $thaiClockScript -StepName 'thai_clock'
# 4) sentences.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $sentencesScript -StepName 'sentences'
# 5) sentence_token.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $sentenceTokenScript -StepName 'sentence_token'
# 6) tag_num.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $tagNumScript -StepName 'tag_num'
# 7) connectors.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $connectorsScript -StepName 'connectors'
# 8) abbreviation.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $abbreviationScript -StepName 'abbreviation'
# 9) tokenize.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $tokenizeScript -StepName 'tokenize'
# 10) sentence_heads.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $sentenceHeadsScript -StepName 'sentence_heads'
# 11) word_pattern.ps1 until "modified documents: 0"
Invoke-StepWithLimit -ScriptPath $wordPatternScript -StepName 'word_pattern'


# === Save new limits to limits.jsonl ===
if ($limitsTableNew.Count -gt 0) {
  $lines = @()
  foreach ($k in $limitsTableNew.Keys) {
    $lines += (@{script=$k;limit=$limitsTableNew[$k]} | ConvertTo-Json -Compress)
  }
  Set-Content -Path $limitsPath -Value $lines
  Write-Host "Updated limits.jsonl with new limits." -ForegroundColor Cyan
}

Write-Host "All steps completed." -ForegroundColor Green
