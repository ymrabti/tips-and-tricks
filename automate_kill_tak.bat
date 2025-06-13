@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "0.0.0.0:5037"') do (
echo Killing process with PID %%a
taskkill /PID %%a /F
)
