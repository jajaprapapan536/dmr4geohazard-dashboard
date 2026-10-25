@echo off
title Geohazard Inspection Dashboard
cd /d "%~dp0"
echo ========================================================
echo   Geological Hazard Inspection Dashboard & GIS Portal
echo   ระบบตรวจสอบและติดตามธรณีพิบัติภัย
echo ========================================================
echo.
echo กำลังเปิดระบบ Dashboard...
"C:\Users\Acer_CT\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run app.py
pause
