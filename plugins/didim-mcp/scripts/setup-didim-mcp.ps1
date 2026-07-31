#requires -Version 5.1
<#
.SYNOPSIS
    Configure the Didim MCP server in the current user's Codex config.toml.

.DESCRIPTION
    Prompts for a personal Didim Vault API key (dv_ format) using hidden input,
    validates it, backs up ~/.codex/config.toml with a timestamp, then writes or
    replaces the [mcp_servers.didim-mcp] block (including an http_headers table
    carrying the key). All other configuration is preserved and not reordered.

    Idempotent: running it repeatedly leaves exactly one didim-mcp block.
    The key is never printed to the console, error messages, or logs, and is
    never written anywhere except the user's own config.toml.

.NOTES
    No administrator privileges required. Restart Codex after running.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# --- Fixed Didim MCP connection settings (do not change auth structure) ---
$ServerUrl      = 'http://49.50.138.22:31083/mcp/'
$StartupTimeout = 120
$HeaderName     = 'X-Didim-Vault-Api-Key'

# Remove every [mcp_servers.didim-mcp] / [mcp_servers.didim-mcp.*] table from a
# TOML document, preserving all other lines and their order. A table spans from
# its header line up to (but not including) the next table header or EOF.
function Remove-DidimBlock {
    param([string]$Content)
    if ([string]::IsNullOrEmpty($Content)) { return '' }
    $lines = $Content -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $inDidim = $false
    foreach ($line in $lines) {
        $trim = $line.Trim()
        if ($trim -match '^\[') {
            # A new TOML table (or array-of-tables) header begins here.
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
Write-Host 'Didim MCP - setup' -ForegroundColor Cyan
Write-Host '-----------------'

# 1. Resolve target paths under the current user's home directory.
$codexDir = Join-Path $HOME '.codex'
$cfgPath  = Join-Path $codexDir 'config.toml'

if (-not (Test-Path -LiteralPath $codexDir)) {
    New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
    Write-Host "Created directory: $codexDir"
}

# 2. Read existing config (UTF-8) if present.
$existing = ''
if (Test-Path -LiteralPath $cfgPath) {
    $existing = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8)
}

# 3. Acquire the key via hidden input (never as a command-line argument).
$secure = Read-Host -Prompt 'Enter your Didim Vault API key (input hidden)' -AsSecureString
$bstr   = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}
finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

# 4. Validate. The dv_ pattern also guarantees no whitespace, newline, quote,
#    or backslash, so it cannot break the TOML basic string.
if ([string]::IsNullOrWhiteSpace($key)) {
    $key = $null
    Write-Error 'No key was entered. Nothing was changed.'
    exit 1
}
if ($key -notmatch '^dv_[A-Za-z0-9_-]{8,}$') {
    $key = $null
    Write-Error 'Invalid key format. A Didim Vault API key must start with "dv_" followed by at least 8 characters of letters, digits, "-", or "_". Nothing was changed.'
    exit 1
}

# 5. Build the replacement block (CRLF for Windows).
$nl = "`r`n"
$block =
    "[mcp_servers.didim-mcp]$nl" +
    "url = ""$ServerUrl""$nl" +
    "startup_timeout_sec = $StartupTimeout$nl" +
    $nl +
    "[mcp_servers.didim-mcp.http_headers]$nl" +
    "$HeaderName = ""$key""$nl"

# 6. Strip any prior didim-mcp tables, then append exactly one fresh block.
$preserved = (Remove-DidimBlock $existing).TrimEnd()
if ([string]::IsNullOrEmpty($preserved)) {
    $final = $block
}
else {
    $final = $preserved + $nl + $nl + $block
}

# 7. Timestamped backup before writing (only when a file already exists).
if (Test-Path -LiteralPath $cfgPath) {
    $stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$cfgPath.backup-$stamp"
    Copy-Item -LiteralPath $cfgPath -Destination $backup -Force
    Write-Host "Backup created: $backup"
}

# 8. Write UTF-8 without BOM.
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($cfgPath, $final, $utf8)

# 9. Scrub secrets from memory. Never echo the key.
$key = $null; $block = $null; $final = $null
[System.GC]::Collect()

Write-Host ''
Write-Host "[OK] Didim MCP configured in: $cfgPath" -ForegroundColor Green
Write-Host '     (Your key was not displayed and was written only to your local config.toml.)'
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Fully quit every Codex window / session.'
Write-Host '  2. Start Codex again.'
Write-Host '  3. Run  /mcp  and confirm the "didim-mcp" server and its tools appear.'
Write-Host ''
