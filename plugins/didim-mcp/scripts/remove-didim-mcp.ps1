#requires -Version 5.1
<#
.SYNOPSIS
    Remove the Didim MCP server block from the current user's Codex config.toml.

.DESCRIPTION
    Deletes only the [mcp_servers.didim-mcp] and [mcp_servers.didim-mcp.*]
    tables. All other MCP servers and general settings are preserved and not
    reordered. A timestamped backup is created before any change. If no Didim
    MCP configuration is present, the script reports that and exits normally.
    Safe to run multiple times. The API key is never printed.

.PARAMETER KillCodexProcesses
    Opt in to closing running Codex processes after removal. Off by default;
    without this switch the script never touches any process.

.PARAMETER KillWithoutConfirmation
    With -KillCodexProcesses, skip the [y/N] prompt.

.PARAMETER ProcessNames
    EXACT ProcessName values (no .exe, no substring) to close. Default: codex.

.NOTES
    No administrator privileges required. Restart Codex after running.
#>
[CmdletBinding()]
param(
    [switch]$KillCodexProcesses,
    [switch]$KillWithoutConfirmation,
    [string[]]$ProcessNames = @('codex')
)

$ErrorActionPreference = 'Stop'

# Offer to close running Codex processes (exact ProcessName match only). Never
# closes this script's own process or ancestors. If launched from inside Codex,
# it does not try to close anything. Only called when -KillCodexProcesses is set.
function Invoke-CodexProcessClose {
    param(
        [string[]]$Names,
        [switch]$KillWithoutConfirmation
    )

    $protected = New-Object System.Collections.Generic.HashSet[int]
    [void]$protected.Add($PID)
    $launchedFromCodex = $false
    $cur = $PID
    for ($i = 0; $i -lt 20 -and $cur -gt 0; $i++) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$cur" -ErrorAction SilentlyContinue
        if (-not $p) { break }
        if ([int]$p.ProcessId -ne $PID) {
            $aname = ($p.Name -replace '\.exe$', '')
            if ($Names -contains $aname) { $launchedFromCodex = $true }
        }
        $cur = [int]$p.ParentProcessId
        if ($cur -gt 0) { [void]$protected.Add($cur) }
    }

    if ($launchedFromCodex) {
        Write-Host ''
        Write-Host 'This script is running inside Codex, so it cannot close the Codex app for you.' -ForegroundColor Yellow
        Write-Host 'Fully quit ALL Codex windows yourself, then start Codex again.'
        return
    }

    $targets = @(
        Get-Process -ErrorAction SilentlyContinue |
        Where-Object { ($Names -contains $_.ProcessName) -and -not $protected.Contains($_.Id) }
    )

    if ($targets.Count -eq 0) {
        Write-Host 'No matching Codex processes are running.'
        return
    }

    Write-Host ''
    Write-Host 'These Codex processes can be closed:' -ForegroundColor Yellow
    $targets | Sort-Object ProcessName, Id | ForEach-Object {
        Write-Host ("  {0}  (PID {1})" -f $_.ProcessName, $_.Id)
    }

    $go = [bool]$KillWithoutConfirmation
    if (-not $go) {
        $ans = Read-Host 'Close them now? [y/N]'   # default: No
        $go = ($ans -match '^(y|yes)$')
    }
    if (-not $go) {
        Write-Host 'Left running. Quit Codex yourself before restarting.'
        return
    }

    foreach ($t in $targets) {
        try {
            Stop-Process -Id $t.Id -Force -ErrorAction Stop
            Write-Host ("  closed {0} (PID {1})" -f $t.ProcessName, $t.Id) -ForegroundColor Green
        }
        catch {
            Write-Host ("  could not close {0} (PID {1}): {2}" -f $t.ProcessName, $t.Id, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

function Remove-DidimBlock {
    param([string]$Content)
    if ([string]::IsNullOrEmpty($Content)) { return '' }
    $lines = $Content -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $inDidim = $false
    foreach ($line in $lines) {
        $trim = $line.Trim()
        if ($trim -match '^\[') {
            if ($trim -match '^\[\s*mcp_servers\.didim-mcp\s*\]$' -or
                $trim -match '^\[\s*mcp_servers\.didim-mcp\.[^\]]+\]$') {
                $inDidim = $true
                continue
            }
            else {
                $inDidim = $false
            }
        }
        if (-not $inDidim) { $out.Add($line) }
    }
    return ($out -join "`r`n")
}

Write-Host ''
Write-Host 'Didim MCP - remove' -ForegroundColor Cyan
Write-Host '------------------'

$codexDir = Join-Path $HOME '.codex'
$cfgPath  = Join-Path $codexDir 'config.toml'

if (-not (Test-Path -LiteralPath $cfgPath)) {
    Write-Host 'No config.toml found; nothing to remove.' -ForegroundColor Green
    exit 0
}

$existing = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8)

$hasBlock = ($existing -match '(?m)^\s*\[\s*mcp_servers\.didim-mcp(\s*\]|\.[^\]]+\])')
if (-not $hasBlock) {
    Write-Host 'No Didim MCP configuration was found; nothing to remove.' -ForegroundColor Green
    exit 0
}

# Timestamped backup before change.
$stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$cfgPath.backup-$stamp"
Copy-Item -LiteralPath $cfgPath -Destination $backup -Force
Write-Host "Backup created: $backup"

$nl    = "`r`n"
$final = (Remove-DidimBlock $existing).TrimEnd()
if (-not [string]::IsNullOrEmpty($final)) { $final += $nl }

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($cfgPath, $final, $utf8)

Write-Host ''
Write-Host "[OK] Didim MCP configuration removed from: $cfgPath" -ForegroundColor Green

# Process closing is opt-in only. Default flow never touches any process.
if ($KillCodexProcesses) {
    try {
        Invoke-CodexProcessClose -Names $ProcessNames -KillWithoutConfirmation:$KillWithoutConfirmation
    }
    catch {
        Write-Host "Note: could not manage Codex processes: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Fully quit ALL Codex windows.'
Write-Host '  2. Start the Codex app again so the change takes effect.'
Write-Host ''
