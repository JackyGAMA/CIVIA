@echo off
title INE - MVP Predicción de Abstención Electoral 2024
echo ====================================================================
echo   INICIANDO MVP DE PREDICCION DE ABSTENCION ELECTORAL INE
echo ====================================================================
echo.
echo Verificando entorno Python...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python en el PATH del sistema.
    pause
    exit /b 1
)

echo.
echo Iniciando servidor FastAPI y abriendo navegador...
echo Si el navegador no abre automaticamente, ingrese a: http://127.0.0.1:8000
echo.
python app.py
pause

