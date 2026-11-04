$ErrorActionPreference = "Stop"
if (!(Test-Path "frontend")) { throw "frontend folder not found." }
Set-Location frontend
if (!(Test-Path "node_modules")) { npm install }
Write-Host "Starting React app at http://localhost:5173"
npm run dev
