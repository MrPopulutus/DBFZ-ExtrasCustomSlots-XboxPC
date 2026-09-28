@echo off
rem Builds both DLLs and the offline test with Zig (pip install ziglang, or a zig.exe on PATH).
rem Usage: build.cmd            then: tests\selector_ui_test.exe "<game>\RED\Binaries\Win64\DRAGON_BALL_FighterZ.exe" out\selector-ui.dll
setlocal
set ZIG=zig
where zig >nul 2>nul || set ZIG=python -m ziglang
if not exist out mkdir out
%ZIG% cc -target x86_64-windows-gnu -shared -O2 -o out\dbfzslots.dll src\dbfzslots.c src\caves.S || goto :fail
%ZIG% cc -target x86_64-windows-gnu -shared -O2 -o out\selector-ui.dll src\selector_ui.c src\selector_ui.S || goto :fail
%ZIG% cc -target x86_64-windows-gnu -O1 -municode -o tests\selector_ui_test.exe tests\selector_ui_test.c || goto :fail
echo Built: out\dbfzslots.dll, out\selector-ui.dll, tests\selector_ui_test.exe
exit /b 0
:fail
echo Build failed.
exit /b 1
