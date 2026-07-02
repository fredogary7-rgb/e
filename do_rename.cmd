@echo off
setlocal enabledelayedexpansion
set count=0
for %%f in (templates\*.html) do (
    powershell -Command "(Get-Content '%%f' -Raw -Encoding UTF8) -replace 'NovaTrade', 'NectarPro' -replace 'novatrade', 'NectarPro' -replace 'NOVATRADE', 'NectarPro' | Set-Content '%%f' -Encoding UTF8 -NoNewline"
    set /a count+=1
    echo !count! traite: %%f
)
echo.
echo TOTAL: %count% fichiers traites