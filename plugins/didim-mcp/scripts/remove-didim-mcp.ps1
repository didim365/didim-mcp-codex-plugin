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

.NOTES
    No administrator privileges required. Restart Codex after running.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

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
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Fully quit every Codex window / session.'
Write-Host '  2. Start Codex again so the change takes effect.'
Write-Host ''
