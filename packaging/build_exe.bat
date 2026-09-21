@echo off
REM ============================================================
REM  build_exe.bat — gera SentinelAI.exe (standalone) via PyInstaller
REM  Rode este arquivo dentro da pasta "packaging" no Windows.
REM  Pré-requisito: Python 3.11+ instalado (python.org, marcar
REM  "Add python.exe to PATH" na instalação).
REM ============================================================

cd /d "%~dp0\.."

echo [1/4] Criando ambiente virtual...
python -m venv .venv_build
call .venv_build\Scripts\activate.bat

echo [2/4] Instalando dependencias do projeto...
pip install --upgrade pip >nul
pip install -r requirements.txt
pip install pyinstaller

echo [3/4] Gerando executavel (isso pode levar alguns minutos)...
pyinstaller --noconfirm --onefile --windowed ^
    --name SentinelAI ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    main.py

echo [4/4] Concluido!
echo Executavel gerado em: dist\SentinelAI.exe
echo.
echo Proximo passo: abra packaging\installer.iss no Inno Setup e clique em Compile
echo para gerar o instalador SentinelAI_Setup.exe
pause
