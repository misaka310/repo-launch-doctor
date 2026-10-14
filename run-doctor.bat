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
for /f %%I in ('%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss-fff"') do set "STAMP=%%I"
if not defined STAMP set "STAMP=%RANDOM%"

set "OUTPUT=reports\%TARGET_NAME%-%STAMP%"

pushd "%~dp0" || exit /b 2

if defined REPO_LAUNCH_DOCTOR_PYTHON (
  "%REPO_LAUNCH_DOCTOR_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=%REPO_LAUNCH_DOCTOR_PYTHON%"
    goto use_python_exe
  )
  goto python_missing
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python

:python_missing
echo Python 3.11 or later was not found. 1>&2
set "EXIT_CODE=2"
goto finish

:use_py
py -3 -m repo_launch_doctor scan "%TARGET%" --output "%OUTPUT%" --fail-on "%FAIL_ON%"
set "EXIT_CODE=%errorlevel%"
goto finish

:use_python
python -m repo_launch_doctor scan "%TARGET%" --output "%OUTPUT%" --fail-on "%FAIL_ON%"
set "EXIT_CODE=%errorlevel%"
goto finish

:use_python_exe
"%PYTHON_EXE%" -m repo_launch_doctor scan "%TARGET%" --output "%OUTPUT%" --fail-on "%FAIL_ON%"
set "EXIT_CODE=%errorlevel%"

:finish
if not defined CI if exist "%OUTPUT%\report.html" start "" "%OUTPUT%\report.html"
popd
exit /b %EXIT_CODE%
