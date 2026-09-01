# Remplace les anciens domaines par le nouveau domaine nectar-pro.cc
$files = @(
    "c:\Users\user\Documents\d\e\static\manifest.json",
    "c:\Users\user\Documents\d\e\static\pwa-register.js",
    "c:\Users\user\Documents\d\e\static\robots.txt",
    "c:\Users\user\Documents\d\e\templates\connexion.html",
    "c:\Users\user\Documents\d\e\templates\index.html",
    "c:\Users\user\Documents\d\e\templates\inscription.html",
    "c:\Users\user\Documents\d\e\templates\market.html",
    "c:\Users\user\Documents\d\e\app.py",
    "c:\Users\user\Documents\d\e\monitor.py",
    "c:\Users\user\Documents\d\e\push_notifications.py"
)

$utf8 = New-Object System.Text.UTF8Encoding($false)

foreach ($f in $files) {
    $c = [System.IO.File]::ReadAllText($f, $utf8)
    $orig = $c
    $c = $c -replace 'nectarpro\.cc', 'nectar-pro.cc'
    $c = $c -replace 'web-production-d52c9\.up\.railway\.app', 'nectar-pro.cc'
    if ($c -ne $orig) {
        [System.IO.File]::WriteAllText($f, $c, $utf8)
        Write-Output "[MODIFIE] $f"
    } else {
        Write-Output "[AUCUN CHANGEMENT] $f"
    }
}
