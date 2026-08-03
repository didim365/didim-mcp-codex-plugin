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

.PARAMETER SkipProcessKill
    Do not offer to close running Codex processes after writing the config.

.PARAMETER KillWithoutConfirmation
    Close matching processes without the [y/N] prompt (still never touches this
    script's own process or its ancestors).

.PARAMETER ProcessNames
    EXACT ProcessName values (no .exe, no substring matching) to close.
    Default: codex. Pass your own, e.g. -ProcessNames @('codex') if the Codex
    process is named differently on your machine.

.NOTES
    No administrator privileges required. Restart Codex after running.
#>
[CmdletBinding()]
param(
    [switch]$SkipProcessKill,
    [switch]$KillWithoutConfirmation,
    [string[]]$ProcessNames = @('codex')
)

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

# Offer to close running Codex processes so the new config.toml is picked up on
# the next launch. Matches EXACT ProcessName values only (no substring). Never
# closes this script's own process or any ancestor. If launched from inside
# Codex, it does not try to close anything and tells the user to quit manually.
function Invoke-CodexProcessClose {
    param(
        [string[]]$Names,
        [switch]$KillWithoutConfirmation
    )

    # Protected PIDs: this process + ancestor chain. Also detect whether an
    # ancestor is itself a Codex process (i.e. we were launched from inside it).
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

    # Standalone window: close only exact-name matches, excluding protected PIDs.
    $targets = @(
        Get-Process -ErrorAction SilentlyContinue |
        Where-Object { ($Names -contains $_.ProcessName) -and -not $protected.Contains($_.Id) }
    )

    if ($targets.Count -eq 0) {
        Write-Host 'No matching Codex processes are running.'
        return
    }

    Write-Host ''
    Write-Host 'These Codex processes can be closed so the new config loads on next launch:' -ForegroundColor Yellow
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

Write-Host ''
Write-Host 'Didim MCP - setup' -ForegroundColor Cyan
Write-Host '-----------------'

# 1. Resolve target paths under the current user's home directory.
$codexDir = Join-Path $HOME '.codex'
$cfgPath  = Join-Path $codexDir 'config.toml'

# 2. Read existing config (UTF-8) if present, and detect an existing Didim block.
$existing = ''
if (Test-Path -LiteralPath $cfgPath) {
    $existing = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8)
}
$hasExisting = ($existing -match '(?m)^\s*\[\s*mcp_servers\.didim-mcp(\s*\]|\.[^\]]+\])')

if ($hasExisting) {
    # Replace / rotate. Never read, print, or compare the old key value.
    Write-Host '기존 Didim MCP 설정을 찾았습니다.'
    Write-Host '새 API Key를 입력하면 기존 API Key와 Didim MCP 설정이 교체됩니다.'
    Write-Host '변경 전 config.toml은 백업됩니다.'
}
else {
    Write-Host 'Didim MCP 최초 설정을 시작합니다.'
    Write-Host '새 API Key를 입력하면 MCP 연결 설정이 생성됩니다.'
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

# 7. Only now (key validated) touch the filesystem: ensure dir, then back up.
if (-not (Test-Path -LiteralPath $codexDir)) {
    New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
    Write-Host "Created directory: $codexDir"
}
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

$action = if ($hasExisting) { 'updated (key replaced)' } else { 'configured' }
Write-Host ''
Write-Host "[OK] Didim MCP $action in: $cfgPath" -ForegroundColor Green
Write-Host '     (Your key was not displayed and was written only to your local config.toml.)'

# 10. Offer to close running Codex processes so a fresh launch reloads
#     config.toml. Some environments do not pick up the change on an immediate
#     restart. Any failure here must NOT fail the (already saved) config.
if (-not $SkipProcessKill) {
    try {
        Invoke-CodexProcessClose -Names $ProcessNames -KillWithoutConfirmation:$KillWithoutConfirmation
    }
    catch {
        Write-Host "Note: could not manage Codex processes: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host '      Your config was saved; just quit Codex manually and restart.'
    }
}

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Fully quit ALL Codex windows (this script cannot always do it for you).'
Write-Host '  2. Start the Codex app again.'
Write-Host '  3. Run  /mcp  and confirm the "didim-mcp" server and its tools appear.'
Write-Host ''
