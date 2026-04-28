@echo off
:: Batch Got Admin Check
:check_Permissions
    echo Administrative permissions required. Detecting permissions...
    
    net session >nul 2>&1
    if %errorLevel% == 0 (
        echo Success: Administrative permissions confirmed.
    ) else (
        echo Failure: Current permissions inadequate.
        echo Requesting elevation...
        powershell -Command "Start-Process '%0' -Verb RunAs"
        exit /b
    )

:: Set install directory
set "INSTALL_DIR=C:\DriveMonitor"
echo Installing to %INSTALL_DIR%...

:: Create directory if it doesn't exist
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

:: Kill existing processes to allow file replacement
echo Stopping existing processes...
taskkill /F /IM DriveMonitor.exe /T >nul 2>&1
taskkill /F /IM DiskInfo64.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: Backup existing config if it exists
if exist "%INSTALL_DIR%\config.json" (
    echo Preserving existing configuration...
    move /Y "%INSTALL_DIR%\config.json" "%INSTALL_DIR%\config.json.tmp" >nul
)

:: Copy files
echo Copying files...
xcopy /E /Y /I "%~dp0*.*" "%INSTALL_DIR%\"

:: Restore config if backup exists, otherwise keep the new one
if exist "%INSTALL_DIR%\config.json.tmp" (
    move /Y "%INSTALL_DIR%\config.json.tmp" "%INSTALL_DIR%\config.json" >nul
)

:: Exclude the batch file itself and the package/dist folders if they are there
del "%INSTALL_DIR%\install.bat" 2>nul
rmdir /S /Q "%INSTALL_DIR%\Package" 2>nul
rmdir /S /Q "%INSTALL_DIR%\ReleaseFolder" 2>nul
rmdir /S /Q "%INSTALL_DIR%\dist" 2>nul
rmdir /S /Q "%INSTALL_DIR%\build" 2>nul

:: Add to Registry for Startup
echo Adding to Startup Registry...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "DriveMonitor" /t REG_SZ /d "\"%INSTALL_DIR%\DriveMonitor.exe\"" /f

:: Start the application
echo Launching Drive Monitor...
cd /d "%INSTALL_DIR%"
start "" "DriveMonitor.exe"

echo.
echo Installation Complete!
echo You can now close this window.
pause
