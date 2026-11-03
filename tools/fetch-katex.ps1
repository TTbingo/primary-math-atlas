# 一次性脚本：取 katex dist 资源到 assets/katex（构建不依赖本脚本）
# 用法：在 PowerShell 中运行  .\tools\fetch-katex.ps1
$ErrorActionPreference = 'Stop'
$Ver = '0.16.22'
$Root = Split-Path -Parent $PSScriptRoot
$Tmp = Join-Path $env:TEMP ("katex-" + [guid]::NewGuid().ToString('N'))
$Dest = Join-Path $Root 'assets\katex'

New-Item -ItemType Directory -Path $Tmp -Force | Out-Null
try {
    Write-Host "npm pack katex@$Ver ..."
    Push-Location $Tmp
    & npm pack "katex@$Ver" 2>&1 | Out-Host
    $tgz = Get-ChildItem -Filter 'katex-*.tgz' | Select-Object -First 1
    if (-not $tgz) { throw 'npm pack 未产出 tgz' }
    & tar -xzf $tgz.FullName
    $dist = Join-Path $Tmp 'package\dist'
    if (-not (Test-Path $dist)) { throw '未找到 package/dist' }

    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Copy-Item (Join-Path $dist 'katex.min.js')  $Dest -Force
    Copy-Item (Join-Path $dist 'katex.min.css') $Dest -Force
    $fonts = Join-Path $Dest 'fonts'
    if (Test-Path $fonts) { Remove-Item $fonts -Recurse -Force }
    Copy-Item (Join-Path $dist 'fonts') $Dest -Recurse -Force
    Set-Content -Path (Join-Path $Dest 'VERSION.txt') -Value $Ver -Encoding UTF8
    Pop-Location

    $js  = Get-Item (Join-Path $Dest 'katex.min.js')
    $css = Get-Item (Join-Path $Dest 'katex.min.css')
    $n   = (Get-ChildItem (Join-Path $Dest 'fonts') -File).Count
    Write-Host "OK  katex.min.js=$($js.Length)B  katex.min.css=$($css.Length)B  fonts=$n 个文件"
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path $Tmp) { Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
