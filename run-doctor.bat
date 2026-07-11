@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%~1"=="" (
  set "TARGET=%SCRIPT_DIR%"
) else (
  for %%I in ("%~1") do set "TARGET=%%~fI"
)
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

if "%~2"=="" (
  set "FAIL_ON=high"
) else (
  set "FAIL_ON=%~2"
)

for %%I in ("%TARGET%") do set "TARGET_NAME=%%~nxI"
if not defined TARGET_NAME set "TARGET_NAME=repository"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss-fff"') do set "STAMP=%%I"
if not defined STAMP set "STAMP=%RANDOM%"

set "OUTPUT=reports\%TARGET_NAME%-%STAMP%"

pushd "%~dp0" || exit /b 2

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m repo_launch_doctor scan "%TARGET%" --output "%OUTPUT%" --fail-on "%FAIL_ON%"
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 (
    echo Python 3.11 or later was not found. 1>&2
    popd
    exit /b 2
  )
  python -m repo_launch_doctor scan "%TARGET%" --output "%OUTPUT%" --fail-on "%FAIL_ON%"
)

set "EXIT_CODE=%errorlevel%"
if not defined CI if exist "%OUTPUT%\report.html" start "" "%OUTPUT%\report.html"
popd
exit /b %EXIT_CODE%
