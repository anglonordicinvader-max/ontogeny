#!/usr/bin/env pwsh
# verify.ps1 — Unified verification script for Ontogeny
# Usage: ./verify.ps1 [-Test] [-Lint] [-Typecheck] [-All]
#
# Runs all verification checks and reports results.

param(
    [switch]$Test,
    [switch]$Lint,
    [switch]$Typecheck,
    [switch]$All
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
$RendererDir = Join-Path $ProjectRoot "desktop/renderer"
$results = @()

function Write-Header($title) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
}

function Run-Check($name, $cmd, $workdir) {
    Write-Header $name
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        if ($workdir) {
            $output = Invoke-Expression "cmd /c `"$cmd`" 2>&1" | Out-String
        } else {
            Push-Location $workdir
            $output = Invoke-Expression "cmd /c `"$cmd`" 2>&1" | Out-String
            Pop-Location
        }
        $exitCode = $LASTEXITCODE
        $sw.Stop()
        if ($output) { Write-Host $output }
        $status = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
        $color = if ($exitCode -eq 0) { "Green" } else { "Red" }
        Write-Host "`n  Result: $status ($($sw.Elapsed.TotalSeconds.ToString('F1'))s)" -ForegroundColor $color
        return @{ Name = $name; Status = $status; Time = $sw.Elapsed.TotalSeconds }
    } catch {
        $sw.Stop()
        Write-Host "`n  Result: ERROR - $($_.Exception.Message)" -ForegroundColor Red
        return @{ Name = $name; Status = "ERROR"; Time = $sw.Elapsed.TotalSeconds }
    }
}

$runAll = $All -or (-not $Test -and -not $Lint -and -not $Typecheck)

# ── Python Checks ──
if ($runAll -or $Test) {
    $results += Run-Check "Python Smoke Tests" "python -m pytest tests/ -v --tb=short" $ProjectRoot
}

if ($runAll -or $Lint) {
    $results += Run-Check "Python Lint (Ruff)" "python -m ruff check src/ backend/ tests/" $ProjectRoot
    $results += Run-Check "Python Lint (Ruff format check)" "python -m ruff format --check src/ backend/ tests/" $ProjectRoot
}

# ── Frontend Checks ──
if ($runAll -or $Typecheck) {
    $results += Run-Check "TypeScript Type Check" "npx tsc --noEmit" $RendererDir
}

if ($runAll -or $Lint) {
    $results += Run-Check "ESLint" "npx eslint src/ --max-warnings 50" $RendererDir
}

if ($runAll -or $Test) {
    $results += Run-Check "Frontend Build" "npm run build" $RendererDir
}

# ── Summary ──
Write-Header "SUMMARY"
$pass = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$fail = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$err = ($results | Where-Object { $_.Status -eq "ERROR" }).Count
$total = $results.Count

foreach ($r in $results) {
    $color = switch ($r.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "ERROR" { "Red" }
    }
    Write-Host ("  [{0}] {1} ({2:F1}s)" -f $r.Status, $r.Name, $r.Time) -ForegroundColor $color
}

Write-Host ""
if ($fail -eq 0 -and $err -eq 0) {
    Write-Host "  ALL CHECKS PASSED ($total/$total)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  $fail/$total FAILED, $err/$total ERRORS" -ForegroundColor Red
    exit 1
}
