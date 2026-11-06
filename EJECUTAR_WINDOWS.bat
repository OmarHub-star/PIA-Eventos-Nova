@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python scripts\init_env.py
echo Abre http://localhost:8000/docs y usa los tokens de .env
python scripts\serve.py
goto end
:error
echo No se completaron los requisitos. Revisa el mensaje anterior.
pause
:end
