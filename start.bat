@echo off
setlocal
cd /d "%~dp0"
title AI Study Buddy

rem ---- 1. find Python ----
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python was not found on this computer.
  echo Trying to install Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo If the install worked, CLOSE this window and double-click start.bat again.
  echo Otherwise install Python from https://www.python.org/downloads/
  echo and tick the box Add python.exe to PATH during setup.
  pause
  exit /b 1
)

rem ---- 2. private environment inside this folder ----
if not exist ".venv\Scripts\python.exe" (
  echo Creating the environment, first time only...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Could not create the environment.
    pause
    exit /b 1
  )
)

rem ---- 3. install libraries once ----
if not exist ".venv\.installed" (
  echo Installing libraries. This takes a few minutes the first time. Internet is required.
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Installation failed. Check the internet connection and run start.bat again.
    pause
    exit /b 1
  )
  echo done> ".venv\.installed"
)

rem ---- 4. skip the Streamlit email question ----
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  mkdir "%USERPROFILE%\.streamlit" 2>nul
  > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
  >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

rem ---- 5. run ----
echo.
echo Starting AI Study Buddy. Your browser will open by itself.
echo Keep this window open while using the app. Close it to stop.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
