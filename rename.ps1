$ErrorActionPreference = 'Continue'
$root = 'c:\Users\user\Documents\d\e'
$logFile = Join-Path $root '_rename_log.txt'

'=== NovaTrade -> NectarPro Rename Log ===' | Out-File -FilePath $logFile -Encoding UTF8
$total = 0

# Patterns to replace (order matters: case-sensitive first)
$replacements = @(
    @{pattern='NovaTrade'; replacement='NectarPro'},
    @{pattern='NOVATRADE'; replacement='NECTARPRO'},
    @{pattern='novatrade'; replacement='nectarpro'},
    @{pattern='nova-trade'; replacement='nectarpro'},
    @{pattern='nova_trade'; replacement='nectar_pro'}
)

$skipDirs = @('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'migrations')
$skipExts = @('.exe', '.dll', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.mp4', '.webm', '.mov', '.avi', '.mp3', '.wav', '.ogg', '.pdf', '.db', '.pyc', '.tmp', '.webp')
$skipNames = @('rename_nectarpro.py', 'rename.ps1', 'run_rename.cmd')

Get-ChildItem -Path $root -Recurse -File | ForEach-Object {
    $path = $_.FullName
    $name = $_.Name
    $ext = $_.Extension.ToLower()
    $dir = Split-Path $path -Parent
    
    # Skip logic
    $skip = $false
    if ($name -in $skipNames -or $ext -in $skipExts) { $skip = $true }
    foreach ($d in $skipDirs) {
        if ($dir -match "\\$d\\" -or $dir -match "\\$d`$") { $skip = $true; break }
    }
    
    if (-not $skip) {
        try {
            $content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
            $newContent = $content
            
            foreach ($r in $replacements) {
                # Case-sensitive for exact matches with proper casing, case-insensitive for others
                if ($r.pattern -cmatch '^[a-z]') {
                    # starts with lowercase = case-insensitive
                    $newContent = $newContent -ireplace $r.pattern, $r.replacement
                } else {
                    # starts with uppercase = case-sensitive
                    $newContent = $newContent -creplace $r.pattern, $r.replacement
                }
            }
            
            if ($newContent -cne $content) {
                [System.IO.File]::WriteAllText($path, $newContent, [System.Text.Encoding]::UTF8)
                $rel = $path.Substring($root.Length + 1)
                "UPDATED: $rel" | Out-File -FilePath $logFile -Append -Encoding UTF8
                $total++
            }
        }
        catch {
            $rel = $path.Substring($root.Length + 1)
            "FAILED: $rel - $_" | Out-File -FilePath $logFile -Append -Encoding UTF8
        }
    }
}

"Total: $total files updated" | Out-File -FilePath $logFile -Append -Encoding UTF8
Write-Host "Done. $total files updated. See _rename_log.txt for details."