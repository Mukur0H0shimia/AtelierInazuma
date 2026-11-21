@echo off
rem Compile le lecteur natif (Visual Studio Build Tools 2026, MSVC x64) : lecteur.exe dans ce dossier.
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>nul
cd /d "%~dp0"
cl /nologo /O2 /EHsc /std:c++17 /utf-8 /W3 /Fe:lecteur.exe /Fo:src\ src\lecteur.cpp /link /SUBSYSTEM:WINDOWS shell32.lib
