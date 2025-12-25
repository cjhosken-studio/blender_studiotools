@echo off
setlocal enabledelayedexpansion

REM Directory containing preload.bat and load.py
set "SCRIPT_DIR=%~dp0"

REM Arguments from Popen
set "REAL_EXE=%~1"
set "FILE_PATH=%~2"

if "%FILE_PATH%"=="" (
    echo Missing file_path argument
    exit /b 1
)

if "%REAL_EXE%"=="" (
    echo Missing exe_path argument
    exit /b 1
)


REM ==============================================
REM 4. INSTALL PYTHON DEPENDENCIES
REM ==============================================
REM Get Blender installation directory
for %%I in ("%REAL_EXE%") do set "BLENDER_DIR=%%~dpI"

for /f "delims=" %%D in ('
    dir "%BLENDER_DIR%" /ad /b ^| sort /r
') do (
    if exist "%BLENDER_DIR%%%D\python\bin\python.exe" (
        set "BLENDER_PYTHON=%BLENDER_DIR%%%D\python\bin\python.exe"
        goto :found_python
    )
)

:found_python

if exist "%SCRIPT_DIR%requirements.txt" (
    echo Installing Python dependencies...
    "!BLENDER_PYTHON!" -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
)


set "PYTHONPATH=%PYTHONPATH%;%SCRIPT_DIR%.."
set "INPIPE=1"

echo Launching Blender...
"%REAL_EXE%" --python-use-system-env --python %SCRIPT_DIR%\load.py "%FILE_PATH%"