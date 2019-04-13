
REM ### Create a Conda package for Caelus Python Library

@ECHO OFF

REM # Run from the script directory
cd "%~dp0" || exit /B 1

set caelus_version="v1.0.1"
set script_dir="%~dp0"

REM Activate base/root environment for build and constructor
call activate.bat

set arch_type="win-64"

if not exist channels\%arch_type% (
    mkdir channels\%arch_type%
)

REM Build the CPL package suitable for bundling with conda installer
call conda build --output-folder channels caelus

REM Create the installer that bundles CPL and its dependencies
cd installer
call python generate_construct.py
call constructor --platform=win-64 .
dir caelus*.exe
cd ..

call deactivate.bat
