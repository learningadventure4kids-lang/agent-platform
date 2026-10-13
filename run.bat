@echo off
setlocal enabledelayedexpansion
title Aria Agent Platform - Launcher

echo ================================================================
echo   Aria Agent Platform - Local Launcher
echo ================================================================
echo.

REM Postgres + pgvector, the FastAPI backend, and the knowledge worker run
REM via Docker Compose (RAG/knowledge-base needs pgvector, which SQLite
REM can't provide). The admin dashboard runs locally via npm for fast
REM dev-reload. See README.md "Local Postgres without Docker" for the
REM manual alternative.

REM --- 1. Check Docker ---
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker was not found on PATH.
    echo Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and re-run this script.
    pause
    exit /b 1
)
docker compose version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "docker compose" is not available. Update Docker Desktop.
    pause
    exit /b 1
)
echo [OK] Docker found.

REM --- 2. Check Ollama ---
where ollama >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Ollama was not found on PATH.
    echo Install it from https://ollama.com/download and re-run this script.
    pause
    exit /b 1
)
echo [OK] Ollama found.

REM --- 3. Check Node/npm ---
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH.
    echo Install Node 18+ from https://nodejs.org/ and re-run this script.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    pause
    exit /b 1
)
echo [OK] Node/npm found.

REM --- 4. Ensure env files exist ---
if not exist backend\.env (
    copy backend\.env.example backend\.env >nul
    echo Created backend\.env from .env.example -- edit it if you need custom settings.
)
if not exist .env (
    copy .env.example .env >nul
    echo Created root .env from .env.example (Postgres credentials for docker-compose).
)
if not exist frontend\.env (
    copy frontend\.env.example frontend\.env >nul
)

REM --- 5. Check/pull Ollama models ---
set MODEL=qwen3:8b
set EMBED_MODEL=nomic-embed-text
for /f "usebackq tokens=1,2 delims==" %%A in ("backend\.env") do (
    if "%%A"=="OLLAMA_MODEL" set MODEL=%%B
    if "%%A"=="EMBEDDING_MODEL" set EMBED_MODEL=%%B
)

echo Checking for Ollama model "%MODEL%"...
ollama list | findstr /I "%MODEL%" >nul
if errorlevel 1 (
    echo Pulling %MODEL% ...
    ollama pull %MODEL%
) else (
    echo [OK] Model %MODEL% already available.
)

echo Checking for Ollama embedding model "%EMBED_MODEL%"...
ollama list | findstr /I "%EMBED_MODEL%" >nul
if errorlevel 1 (
    echo Pulling %EMBED_MODEL% ...
    ollama pull %EMBED_MODEL%
) else (
    echo [OK] Model %EMBED_MODEL% already available.
)

REM --- 6. Start Postgres + backend + worker via Docker Compose ---
echo Starting Postgres + pgvector, backend API, and the knowledge worker...
docker compose up -d --build

REM --- 7. Admin dashboard: npm dependencies ---
cd frontend
if not exist node_modules (
    echo Installing admin dashboard dependencies (first run only)...
    call npm install
)
cd ..

REM --- 8. Start admin dashboard in its own window ---
echo Starting admin dashboard on http://localhost:5178 ...
start "Aria Platform - Admin Dashboard" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 5 /nobreak >nul
start "" "http://localhost:5178"

echo.
echo ================================================================
echo   Backend:         http://localhost:8000  (docs at /docs)
echo   Admin dashboard: http://localhost:5178
echo   Postgres:        localhost:5432
echo.
echo   Public agent tokens for the seeded sample agents were logged by
echo   the backend container -- run:
echo     docker compose logs backend
echo   and look for lines starting with "Seeded token".
echo.
echo   Docker services (postgres/backend/worker) keep running until you
echo   stop them with: docker compose down
echo   Close the admin dashboard window to stop that dev server.
echo ================================================================
pause
