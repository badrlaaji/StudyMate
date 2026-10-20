# Start the three services in their own windows: API :8000, Spring :8080, web :3000.
# Usage (from the repository root): .\scripts\dev.ps1
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"

# Spring reads its settings from environment variables (SPRING_DATASOURCE_*):
# load .env into this process, the child windows inherit it.
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=\s][^=]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
        }
    }
}

$api = "Set-Location '$root'; uv run uvicorn api.main:app --reload --port 8000"
$core = "Set-Location '$(Join-Path $root 'core')'; .\mvnw.cmd spring-boot:run"
$web = "Set-Location '$(Join-Path $root 'frontend')'; npm run dev"

foreach ($command in @($api, $core, $web)) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $command
}
Write-Host "API http://localhost:8000 | Spring http://localhost:8080 | Web http://localhost:3000"
