@echo off
setlocal

if "%~1"=="" (
  set "TARGET=."
) else (
  set "TARGET=%~1"
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m repo_launch_doctor scan "%TARGET%" --output "reports\repo-launch-doctor" --fail-on none
) else (
  python -m repo_launch_doctor scan "%TARGET%" --output "reports\repo-launch-doctor" --fail-on none
)

set "EXIT_CODE=%errorlevel%"
if exist "reports\repo-launch-doctor\report.html" start "" "reports\repo-launch-doctor\report.html"
exit /b %EXIT_CODE%
