@echo off
setlocal
cd /d %~dp0\..

if exist .venv311\Scripts\python.exe (
    set PYTHON_EXE=.venv311\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

%PYTHON_EXE% -m uvicorn backend.realtime.app:app --host 0.0.0.0 --port 8001 --reload
endlocal
