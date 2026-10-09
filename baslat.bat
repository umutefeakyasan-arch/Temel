@echo off
chcp 65001 >nul
title T.E.M.E.L. Baslatici
echo Groq API anahtarini yapistir ve Enter'a bas.
echo (Anahtar sadece bu pencere icin kullanilir, bilgisayara kaydedilmez.)
set /p GROQ_API_KEY=Anahtar: 
if "%GROQ_API_KEY%"=="" (
    echo Anahtar girilmedi, cikiliyor.
    pause
    exit /b 1
)
python temel.py
pause
