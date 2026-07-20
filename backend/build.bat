@echo off
setlocal
echo Building Ontogeny Backend...
python -m pip install -r requirements-ui.txt
python -m pip install pyinstaller
python build_demo.py
if errorlevel 1 exit /b %errorlevel%
echo Build complete!
endlocal
