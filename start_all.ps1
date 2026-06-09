$ErrorActionPreference = "Stop"

Write-Host "Starting Registry service on port 10000..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "registry"

Start-Sleep -Seconds 2

Write-Host "Starting Tax Agent on port 10102..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "tax_agent"

Write-Host "Starting Compliance Agent on port 10103..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "compliance_agent"

Write-Host "Starting Privacy Agent on port 10104..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "privacy_agent"

Start-Sleep -Seconds 3

Write-Host "Starting Law Agent on port 10101..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "law_agent"

Start-Sleep -Seconds 3

Write-Host "Starting Customer Agent on port 10100..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "python", "-m", "customer_agent"

Write-Host ""
Write-Host "All services started:"
Write-Host "  Registry:         http://localhost:10000"
Write-Host "  Customer Agent:   http://localhost:10100"
Write-Host "  Law Agent:        http://localhost:10101"
Write-Host "  Tax Agent:        http://localhost:10102"
Write-Host "  Compliance Agent: http://localhost:10103"
Write-Host "  Privacy Agent:    http://localhost:10104"
Write-Host ""
Write-Host "Run test_client.py to send a query:"
Write-Host "  uv run python test_client.py"
Write-Host ""
Write-Host "To stop, close this PowerShell window or kill python processes manually."
