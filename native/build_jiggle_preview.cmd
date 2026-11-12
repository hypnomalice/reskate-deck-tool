@echo off
setlocal
where cl.exe >nul 2>&1
if errorlevel 1 (
 echo Run this script from an x64 Visual Studio 2022 developer command prompt.
 exit /b 1
)
set "SPRINGS_ROOT=%~dp0.."
if not exist "%~dp0build" mkdir "%~dp0build"
cl /nologo /std:c++20 /EHsc /MT /O2 /LD "%~dp0jiggle_preview.cpp" /Fo:"%~dp0build\jiggle_preview.obj" /link /OUT:"%SPRINGS_ROOT%\assets\jiggle-runtime\jiggle_preview.dll" /IMPLIB:"%~dp0build\jiggle_preview.lib"
exit /b %errorlevel%
