#requires -Version 5.1
<#
.SYNOPSIS
    Remove the legacy Didim MCP server block from the current user's Codex config.toml.

.DESCRIPTION
    Didim MCP now connects over OAuth. The plugin declares the hosted MCP server
    itself (see .codex-plugin/plugin.json) and Codex signs you in through
    OAuth sign-in, so no API key or auth header is configured any more.

    A leftover [mcp_servers.didim-mcp] block in config.toml — written by plugin
    versions 0.1.x — SHADOWS the plugin-provided server: Codex keeps using the
    old URL and the old X-Didim-Vault-Api-Key header, and the OAuth sign-in
    never happens. This script deletes that block so the plugin's OAuth server
    takes over.

    It deletes only the [mcp_servers.didim-mcp] and [mcp_servers.didim-mcp.*]
    tables. All other MCP servers and general settings are preserved and not
    reordered. A timestamped backup is created before any change. If no legacy
    Didim MCP configuration is present, the script reports that and exits
    normally. Safe to run multiple times. No credential value is ever read back,
    compared, printed, or logged.

.PARAMETER KillCodexProcesses
    Opt in to closing running Codex processes after removal. Off by default;
    without this switch the script never touches any process.

.PARAMETER KillWithoutConfirmation
    With -KillCodexProcesses, skip the [y/N] prompt.

.PARAMETER ProcessNames
    EXACT ProcessName values (no .exe, no substring) to close. Default: codex.

.NOTES
    No administrator privileges required. Restart Codex after running, then use
    'codex mcp login didim-mcp' to sign in with your Microsoft account.
#>
[CmdletBinding()]
param(
    [switch]$KillCodexProcesses,
    [switch]$KillWithoutConfirmation,
    [string[]]$ProcessNames = @('codex')
)

$ErrorActionPreference = 'Stop'

# Render Korean (non-ASCII) output correctly on Windows PowerShell 5.1 consoles.
try {
    [Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding           = [System.Text.UTF8Encoding]::new($false)
}
catch { }

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

# Remove every [mcp_servers.didim-mcp] / [mcp_servers.didim-mcp.*] table from a
# TOML document, preserving all other lines and their order. A table spans from
# its header line up to (but not including) the next table header or EOF. This
# takes the whole legacy block with it: url, startup_timeout_sec, and the
# http_headers / env_http_headers sub-tables that carried the API key.
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
Write-Host 'Didim MCP - legacy config cleanup (OAuth migration)' -ForegroundColor Cyan
Write-Host '--------------------------------------------------'

$codexDir = Join-Path $HOME '.codex'
$cfgPath  = Join-Path $codexDir 'config.toml'

if (-not (Test-Path -LiteralPath $cfgPath)) {
    Write-Host 'No config.toml found; nothing to clean up.' -ForegroundColor Green
    Write-Host 'The plugin already provides the Didim MCP server.'
    Write-Host 'Sign in with:  codex mcp login didim-mcp'
    exit 0
}

$existing = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8)

$hasBlock = ($existing -match '(?m)^\s*\[\s*mcp_servers\.didim-mcp(\s*\]|\.[^\]]+\])')
if (-not $hasBlock) {
    Write-Host 'No legacy Didim MCP configuration was found; nothing to clean up.' -ForegroundColor Green
    Write-Host 'The plugin already provides the Didim MCP server.'
    Write-Host 'Sign in with:  codex mcp login didim-mcp'
    exit 0
}

Write-Host 'Legacy [mcp_servers.didim-mcp] configuration found.' -ForegroundColor Yellow
Write-Host 'It will be removed so the plugin-provided OAuth connection can take over.'
Write-Host 'Other MCP servers and settings are left untouched.'

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

# The removed block may have carried an API key header. Never echo its value.
$existing = $null
[System.GC]::Collect()

Write-Host ''
Write-Host "[OK] Legacy Didim MCP configuration removed from: $cfgPath" -ForegroundColor Green
Write-Host '     legacy credential removed (its value was never displayed or logged).'
Write-Host '     Your old backup files still contain it - delete them if you no longer need them.'

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
Write-Host '  2. Start the Codex app again.'
Write-Host '  3. Sign in:  codex mcp login didim-mcp'
Write-Host '     Complete the Microsoft login in the browser. No API key is needed.'
Write-Host '  4. Run  /mcp  and confirm "didim-mcp" is connected.'
Write-Host ''
