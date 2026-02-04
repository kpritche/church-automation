@echo off
REM Setup script to prepare deployment directory with all required files and structure

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: %0 ^<deployment-directory-path^>
    echo.
    echo Example:
    echo   %0 C:\church-automation-deployment
    echo.
    echo This script will:
    echo   1. Create the deployment directory
    echo   2. Copy packages\, assets\, and Docker files from repo
    echo   3. Create secrets\ directory
    echo   4. Create a template .env file
    echo.
    exit /b 1
)

set "DEPLOY_DIR=%1"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo 🚀 Setting up Church Automation deployment directory...
echo    Target: %DEPLOY_DIR%
echo.

REM Create deployment directory
if exist "%DEPLOY_DIR%" (
    echo ⚠️  Directory already exists: %DEPLOY_DIR%
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" (
        echo Aborted.
        exit /b 1
    )
) else (
    mkdir "%DEPLOY_DIR%"
    echo ✓ Created directory: %DEPLOY_DIR%
)

REM Copy required directories
echo.
echo Copying files from repository...

if exist "%SCRIPT_DIR%\packages" (
    echo Copying packages\...
    xcopy "%SCRIPT_DIR%\packages" "%DEPLOY_DIR%\packages" /E /I /Y >nul
    echo ✓ Copied packages\
) else (
    echo ✗ ERROR: packages\ directory not found in repo
    exit /b 1
)

if exist "%SCRIPT_DIR%\assets" (
    echo Copying assets\...
    xcopy "%SCRIPT_DIR%\assets" "%DEPLOY_DIR%\assets" /E /I /Y >nul
    echo ✓ Copied assets\
) else (
    echo ✗ ERROR: assets\ directory not found in repo
    exit /b 1
)

REM Copy Docker files
for %%F in (Dockerfile docker-compose.yml .dockerignore) do (
    if exist "%SCRIPT_DIR%\%%F" (
        copy "%SCRIPT_DIR%\%%F" "%DEPLOY_DIR%\%%F" >nul
        echo ✓ Copied %%F
    ) else (
        echo ⚠️  Warning: %%F not found
    )
)

REM Create secrets directory
if not exist "%DEPLOY_DIR%\secrets" (
    mkdir "%DEPLOY_DIR%\secrets"
    echo ✓ Created secrets\ directory
) else (
    echo ✓ secrets\ directory already exists
)

REM Create template .env file
echo.
echo Creating template .env file...

(
echo # Planning Center Online API Credentials
echo # Get these from: https://api.planningcenteronline.com/oauth/applications
echo PCO_CLIENT_ID=your_planning_center_client_id_here
echo PCO_SECRET=your_planning_center_secret_or_pat_here
echo.
echo # Announcements Website URL
echo ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
echo.
echo # GCP Credentials filename (optional - for AI text summarization^)
echo GCP_CREDENTIALS_FILENAME=gcp-credentials.json
) > "%DEPLOY_DIR%\.env.template"

echo ✓ Created .env.template

if not exist "%DEPLOY_DIR%\.env" (
    copy "%DEPLOY_DIR%\.env.template" "%DEPLOY_DIR%\.env" >nul
    echo ✓ Created .env (from template^)
    echo.
    echo ⚠️  IMPORTANT: Edit .env and add your Planning Center API credentials
    echo    File: %DEPLOY_DIR%\.env
) else (
    echo ✓ .env already exists (not overwritten^)
)

REM Create template slides_config.json
echo.
echo Creating template configuration files...

(
echo {
echo   "service_type_ids": [1041663, 78127, 1145553],
echo   "sheet_music_service_type_ids": [78127],
echo   "prayer_lists": {
echo     "refresh_before_fetch": true,
echo     "timeout_seconds": 10,
echo     "military_first_name_only": false,
echo     "concerns": {"id": 4688551, "name": "Prayer List"},
echo     "memory_care": {"id": 4742895, "name": "Memory Care"},
echo     "military": {"id": 4742806, "name": "Active Military"}
echo   }
echo }
) > "%DEPLOY_DIR%\secrets\slides_config.json.template"

echo ✓ Created slides_config.json.template

REM Directory structure summary
echo.
echo ✅ Deployment directory ready!
echo.
echo Directory structure:
for /d %%D in ("%DEPLOY_DIR%\*") do (
    echo   %%~nxD\
)

echo.
echo 📋 Next steps:
echo.
echo 1. Edit .env file with your Planning Center credentials:
echo    %DEPLOY_DIR%\.env
echo.
echo 2. (Optional^) Create slides_config.json with your service type IDs:
echo    copy "%DEPLOY_DIR%\secrets\slides_config.json.template" "%DEPLOY_DIR%\secrets\slides_config.json"
echo    (Edit with your actual service IDs^)
echo.
echo 3. (Optional^) Add GCP credentials for AI summarization:
echo    copy %%USERPROFILE%%\Downloads\gcp-credentials.json "%DEPLOY_DIR%\secrets\"
echo.
echo 4. Build the container:
echo    cd %DEPLOY_DIR%
echo    docker-compose build
echo.
echo 5. Start the container:
echo    docker-compose up -d
echo.
echo 6. Access the web UI:
echo    http://localhost:8000
echo.
