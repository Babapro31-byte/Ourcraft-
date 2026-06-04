$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\OurCraft 2.lnk")
$Shortcut.TargetPath  = "$PSScriptRoot\Ourcraft2.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.WindowStyle = 1
# Oyun penceresinin ikonu varsa kullan, yoksa varsayilan
$ico = "$PSScriptRoot\ourcraft2\textures\pack\grass_top.png"
if (Test-Path $ico) {
    # .png ikonunu kullanamayiz, .ico yok ise python exe ikonunu kullan
    $Shortcut.IconLocation = (Get-Command python.exe).Source
}
$Shortcut.Save()
Write-Host "Masaustu kisayolu olusturuldu: $env:USERPROFILE\Desktop\OurCraft 2.lnk"
