@echo off
echo Building Ontogeny Backend...
pip install -r requirements-ui.txt
pip install pyinstaller
pyinstaller backend.spec --clean
echo Build complete!
pause
