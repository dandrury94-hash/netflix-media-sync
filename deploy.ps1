function Clear-Port8080 {
    $containers = docker ps -q --filter "publish=8080"
    if ($containers) {
        Write-Host "  Clearing containers holding port 8080..." -ForegroundColor DarkGray
        docker stop $containers | Out-Null
        docker rm $containers | Out-Null
    }
}

function Test-Streamarr {
    $attempts = 10
    Start-Sleep -Seconds 2
    Write-Host "  Checking http://localhost:8080 " -ForegroundColor DarkGray -NoNewline
    for ($i = 1; $i -le $attempts; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -lt 500) {
                Write-Host " OK" -ForegroundColor Green
                Write-Host ""
                Write-Host "  Streamarr is back up -> http://localhost:8080" -ForegroundColor Green
                return
            }
        } catch {}
        Write-Host "." -ForegroundColor DarkGray -NoNewline
    }
    Write-Host ""
    Write-Host ""
    Write-Host "  Container did not respond after $attempts seconds." -ForegroundColor Red
    Write-Host "  Run: docker compose logs streamarr" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  Streamarr Deploy" -ForegroundColor Cyan
Write-Host "  --------------------------------" -ForegroundColor DarkGray
Write-Host "  [1] Restart  - code change (.py / .html / .css / .js)" -ForegroundColor White
Write-Host "  [2] Rebuild  - new package (requirements.txt changed)" -ForegroundColor White
Write-Host "  [Q] Quit" -ForegroundColor DarkGray
Write-Host ""

$choice = Read-Host "  Choose"

switch ($choice.Trim().ToUpper()) {
    "1" {
        Write-Host ""
        Write-Host "  Restarting container..." -ForegroundColor Yellow
        docker compose restart streamarr
        if ($?) {
            Write-Host ""
            Test-Streamarr
        }
    }
    "2" {
        Write-Host ""
        Write-Host "  Stopping container..." -ForegroundColor Yellow
        docker compose down
        Clear-Port8080
        Write-Host ""
        Write-Host "  Rebuilding image and starting..." -ForegroundColor Yellow
        docker compose up --build -d
        if ($?) {
            Write-Host ""
            Test-Streamarr
        }
    }
    "Q" {
        Write-Host ""
    }
    default {
        Write-Host ""
        Write-Host "  Invalid choice." -ForegroundColor Red
    }
}
