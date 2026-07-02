Get-ChildItem -Path "templates\*.html" | ForEach-Object {
    $content = Get-Content -Path $_.FullName -Raw -Encoding UTF8
    $content = $content -replace 'novatrade', 'NectarPro'
    $content = $content -replace 'NovaTrade', 'NectarPro'
    $content = $content -replace 'NOVATRADE', 'NectarPro'
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
}
Write-Host "Termine"