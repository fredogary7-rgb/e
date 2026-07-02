$files = Get-ChildItem -Path "templates\*.html"
$total = $files.Count
$modified = 0

foreach ($f in $files) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content
    # Remplacer toutes les variantes de casse
    $content = $content -replace 'NovaTrade', 'NectarPro'
    $content = $content -replace 'novatrade', 'NectarPro'
    $content = $content -replace 'NOVATRADE', 'NectarPro'
    if ($content -ne $original) {
        Set-Content $f.FullName -Value $content -Encoding UTF8 -NoNewline
        Write-Host "MODIFIE: $($f.Name)"
        $modified++
    } else {
        Write-Host "AUCUN  : $($f.Name)"
    }
}
Write-Host ""
Write-Host "$modified fichiers modifies sur $total"