# Fortress AI - ROCm Startup Script for Windows
# This script starts all services with ROCm acceleration

Write-Host "=== Fortress AI - ROCm Startup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop and ensure:" -ForegroundColor Yellow
    Write-Host "  1. Docker Desktop is running" -ForegroundColor White
    Write-Host "  2. WSL 2 backend is enabled (Settings > General)" -ForegroundColor White
    Write-Host "  3. ROCm support is configured in WSL 2" -ForegroundColor White
    Write-Host ""
    Write-Host "After starting Docker Desktop, run this script again." -ForegroundColor Yellow
    exit 1
}

# Check if .env file exists
Write-Host ""
Write-Host "Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "✗ .env file not found" -ForegroundColor Red
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.template .env
    Write-Host "✓ Created .env file" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Please edit .env and configure:" -ForegroundColor Yellow
    Write-Host "  - HUGGING_FACE_HUB_TOKEN (required for model download)" -ForegroundColor White
    Write-Host "  - TAVILY_API_KEY (for web search)" -ForegroundColor White
    Write-Host "  - CLERK_* keys (for authentication)" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Press Enter to continue or Ctrl+C to exit and configure .env"
} else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
}

# Start services
Write-Host ""
Write-Host "Starting services with ROCm..." -ForegroundColor Yellow
Write-Host ""

# Remove version warning by using docker compose (without hyphen)
docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Services Started Successfully ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  • PostgreSQL:    http://localhost:5432" -ForegroundColor White
    Write-Host "  • Redis:         http://localhost:6379" -ForegroundColor White
    Write-Host "  • Qdrant:        http://localhost:6333" -ForegroundColor White
    Write-Host "  • Qwen (ROCm):   http://localhost:8001" -ForegroundColor White
    Write-Host "  • Backend API:   http://localhost:8080" -ForegroundColor White
    Write-Host "  • Frontend:      http://localhost:3000" -ForegroundColor White
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Wait for Qwen model to load (5-10 minutes first time)" -ForegroundColor White
    Write-Host "     Monitor: docker logs qwen-3.6-27b -f" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Check service health:" -ForegroundColor White
    Write-Host "     docker compose ps" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. View logs:" -ForegroundColor White
    Write-Host "     docker compose logs -f" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  4. Access the application:" -ForegroundColor White
    Write-Host "     http://localhost:3000" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To stop services: docker compose down" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    Write-Host "Check the error messages above for details" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  • Docker Desktop not running" -ForegroundColor White
    Write-Host "  • Ports already in use" -ForegroundColor White
    Write-Host "  • ROCm drivers not installed in WSL 2" -ForegroundColor White
    exit 1
}

# Made with Bob
