@echo off
setlocal
if not defined LUAU_ROOT (
 echo Set LUAU_ROOT to the Luau source folder and LUAU_LIB to its static library.
 exit /b 1
)
if not defined LUAU_LIB exit /b 1
if not exist "%~dp0build" mkdir "%~dp0build"
cl /nologo /std:c++20 /EHsc /MT /O2 /LD /I "%LUAU_ROOT%\VM\include" /I "%LUAU_ROOT%\Common\include" /I "%LUAU_ROOT%\Compiler\include" /I "%LUAU_ROOT%\Ast\include" "%~dp0shaker_preview.cpp" /Fo:"%~dp0build\shaker_preview.obj" /link /OUT:"%~dp0..\assets\shaker-runtime\shaker_preview.dll" /IMPLIB:"%~dp0build\shaker_preview.lib" "%LUAU_LIB%"
exit /b %errorlevel%
