$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $rootDir

function Write-NotFoundMessage {
  param([string] $MessageKo, [string] $MessageEn)
  Write-Host "[KO] $MessageKo"
  Write-Host "[EN] $MessageEn"
}

$venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
  $pythonBin = $venvPython
} else {
  $pythonBin = "python"
}

if (-not (Get-Command $pythonBin -ErrorAction SilentlyContinue)) {
  Write-NotFoundMessage "Python 런처를 찾을 수 없습니다. Python이 설치되지 않았거나 PATH를 찾지 못했습니다." "Python runtime was not found. Python is missing or not on PATH."
  Write-NotFoundMessage "설치 가이드는 README.md 또는 README.en.md를 참고하세요." "Refer to README.md or README.en.md for setup guidance."
  exit 127
}

$launcherPath = Join-Path $rootDir "scripts\\launcher.py"
if (-not (Test-Path -LiteralPath $launcherPath)) {
  Write-NotFoundMessage "공통 런처 scripts.launcher가 없습니다. 패키지 배포본을 다시 확인하세요." "Shared launcher scripts.launcher is missing. Verify this release package includes scripts/launcher.py."
  Write-NotFoundMessage "배포 가이드는 README.md/README.en.md를 참고하세요." "See README.md/README.en.md for deployment guidance."
  exit 127
}

function Save-LauncherSecret {
  param(
  [Parameter(Mandatory)] [string] $Account
  )

  $value = [Environment]::GetEnvironmentVariable($Account, "Process")
  if (-not [string]::IsNullOrWhiteSpace($value)) {
    if ($Account -eq "AI_API_KEY") {
      & $pythonBin -m scripts.save_secret AI_API_KEY | Out-Null
    } elseif ($Account -eq "OPENDART_API_KEY") {
      & $pythonBin -m scripts.save_secret OPENDART_API_KEY | Out-Null
    } else {
      & $pythonBin -m scripts.save_secret $Account | Out-Null
    }
    [System.Environment]::SetEnvironmentVariable($Account, $null, [System.EnvironmentVariableTarget]::Process)
  }
}

Save-LauncherSecret "AI_API_KEY"
Save-LauncherSecret "OPENDART_API_KEY"

& $pythonBin -m scripts.launcher @args
$exitCode = $LASTEXITCODE
exit $exitCode
