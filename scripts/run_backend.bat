@echo off
cd /d %~dp0..
if exist ".venv311\Scripts\python.exe" (
    .venv311\Scripts\python.exe backend_example.py
) else (
    python backend_example.py
)
