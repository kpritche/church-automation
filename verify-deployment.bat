@echo off
REM Quick verification script for Church Automation deployment (Windows)

setlocal enabledelayedexpansion

echo.
echo 0x1F50D Church Automation - Deployment Verification
echo ====================================================
echo.

REM Check Dockerfile exists
echo Checking Dockerfile...
if exist "Dockerfile" (
    echo   ✓ Dockerfile found
) else (
    echo   ✗ Dockerfile not found
    exit /b 1
)

REM Check docker-compose file exists
echo Checking docker-compose.yml...
if exist "docker-compose.yml" (
    echo   ✓ docker-compose.yml found
) else (
    echo   ✗ docker-compose.yml not found
    exit /b 1
)

REM Check README
echo Checking README-DEPLOYMENT.md...
if exist "README-DEPLOYMENT.md" (
    echo   ✓ README-DEPLOYMENT.md found
) else (
    echo   ✗ README-DEPLOYMENT.md not found
    exit /b 1
)

REM Check packages
echo Checking packages...
for %%P in (shared announcements bulletins slides web_ui) do (
    if exist "packages\%%P" (
        echo   ✓ packages\%%P found
    ) else (
        echo   ✗ packages\%%P not found
        exit /b 1
    )
)

REM Check assets
echo Checking assets...
if exist "assets" (
    echo   ✓ assets directory found
) else (
    echo   ✗ assets directory not found
    exit /b 1
)

echo.
echo ====================================================
echo All checks passed!
echo.
echo Next steps:
echo 1. Create deployment directory:
echo    mkdir %%USERPROFILE%%\church-automation-deployment\secrets
echo.
echo 2. Copy files:
echo    copy docker-compose.yml %%USERPROFILE%%\church-automation-deployment\
echo    copy Dockerfile %%USERPROFILE%%\church-automation-deployment\
echo.
echo 3. Add credentials to %%USERPROFILE%%\church-automation-deployment\secrets\
echo.
echo 4. Build image:
echo    cd %%USERPROFILE%%\church-automation-deployment
echo    docker build -t church-automation:latest .
echo.
echo 5. Start container:
echo    docker-compose up -d
echo.
echo 6. Access web UI:
echo    http://localhost:8000
echo ====================================================
echo.
