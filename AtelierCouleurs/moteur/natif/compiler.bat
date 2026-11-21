@echo off
rem Compile paquets.dll (lecture rapide des paquets du jeu) avec Visual Studio Build Tools (MSVC x64).
rem Builds paquets.dll (fast pack reading) with Visual Studio Build Tools (MSVC x64).
for %%v in (18 2022 2019) do (
  if exist "C:\Program Files (x86)\Microsoft Visual Studio\%%v\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files (x86)\Microsoft Visual Studio\%%v\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>nul
    goto compile
  )
)
:compile
cd /d "%~dp0"
cl /nologo /O2 /LD /utf-8 /W3 paquets.c /Fe:paquets.dll /link /NOLOGO
del /q paquets.obj paquets.exp paquets.lib 2>nul
