#Requires -Version 5.1
<#
.SYNOPSIS
    Stop the EDI 835 Converter backend and frontend services.

.DESCRIPTION
    First stops all background jobs whose name matches 'edi835-*' (the names
    assigned by start.ps1).  Then falls back to a port scan (ports read from
    deploy.env  -  BACKEND_PORT / FRONTEND_PORT) using Get-NetTCPConnection and
    kills any process still holding those ports.

.NOTES
    Requires PowerShell 5.1 or later.
    Must be run from the same PowerShell session as start.ps1 for the job-name
    lookup to succeed; the port fallback works from any session.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "Stopping EDI 835 Converter services..."
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Graceful shutdown: stop all jobs named edi835-*
# ---------------------------------------------------------------------------
$namedJobs = Get-Job -Name 'edi835-*' -ErrorAction SilentlyContinue

if ($namedJobs) {
    foreach ($job in $namedJobs) {
        Write-Host "Stopping job '$($job.Name)' (ID: $($job.Id), State: $($job.State))..."
        Stop-Job   -Job $job
        Remove-Job -Job $job -Force
        Write-Host "  Job '$($job.Name)' stopped and removed."
    }
} else {
    Write-Host "No 'edi835-*' background jobs found in this session."
    Write-Host "(Jobs are only visible in the session that started them.)"
}

Write-Host ""

# ---------------------------------------------------------------------------
# 2. Port fallback: kill any process still listening on the configured ports
#    Uses Get-NetTCPConnection (available on Windows 8.1+ / Server 2012+).
# ---------------------------------------------------------------------------
function Read-EnvFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $result }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { continue }
        $key = $trimmed.Substring(0, $idx).Trim()
        $val = $trimmed.Substring($idx + 1).Trim()
        $result[$key] = $val
    }
    return $result
}

$root      = Split-Path -Parent $PSScriptRoot
$deployEnv = Read-EnvFile -Path (Join-Path $root 'deploy.env')

$targetPorts = @()
if ($deployEnv.ContainsKey('BACKEND_PORT'))  { $targetPorts += [int]$deployEnv['BACKEND_PORT'] }
if ($deployEnv.ContainsKey('FRONTEND_PORT')) { $targetPorts += [int]$deployEnv['FRONTEND_PORT'] }
if (-not $targetPorts) {
    Write-Host "deploy.env not found or incomplete  -  falling back to default ports 7007/7008."
    $targetPorts = @(7007, 7008)
}

foreach ($port in $targetPorts) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

    if (-not $conns) {
        Write-Host "Port $port : free (no process found)."
        continue
    }

    # There can be multiple connections per port; use OwningProcess of the first
    # LISTEN-state entry, falling back to the first result if none is listening.
    $listenConn = $conns | Where-Object { $_.State -eq 'Listen' }
    $conn       = if ($listenConn) { $listenConn[0] } else { $conns[0] }

    $ownerPid = $conn.OwningProcess

    if (-not $ownerPid -or $ownerPid -eq 0) {
        Write-Host "Port $port : connection found but OwningProcess is 0  -  skipping."
        continue
    }

    $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue

    if ($proc) {
        Write-Host "Port $port : held by '$($proc.Name)' (PID $ownerPid)  -  stopping process."
        Stop-Process -Id $ownerPid -Force
        Write-Host "  PID $ownerPid stopped."
    } else {
        Write-Host "Port $port : OwningProcess PID $ownerPid no longer exists."
    }
}

Write-Host ""
Write-Host "All EDI 835 Converter services stopped."
