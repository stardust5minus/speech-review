param([switch]$SetupOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskSelected = $null
    $taskCandidates = @(
        @{ Exe = 'py'; Args = @('-3.12') },
        @{ Exe = 'py'; Args = @('-3.11') },
        @{ Exe = 'python'; Args = @() }
    )
    foreach ($taskCandidate in $taskCandidates) {
        $taskCommand = Get-Command $taskCandidate.Exe -ErrorAction SilentlyContinue
        if (-not $taskCommand) { continue }
        $taskArgs = $taskCandidate.Args
        try { & $taskCommand.Source @taskArgs -c 'import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)' 2>$null }
        catch { continue }
        if ($LASTEXITCODE -eq 0) { $taskSelected = $taskCandidate; break }
    }
    if (-not $taskSelected) {
        throw 'Install Python 3.11 or 3.12 (64-bit) from https://www.python.org/downloads/windows/ with the Python launcher or Add Python to PATH enabled, then run run.bat again.'
    }
    Write-Host 'Creating the local Python environment...'
    $taskArgs = $taskSelected.Args
    & $taskSelected.Exe @taskArgs -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Check the Python installation.' }
}
& $taskPython -c 'import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) and sys.maxsize > 2**32 else 1)'
if ($LASTEXITCODE -ne 0) { throw 'This .venv needs Python 3.11 or 3.12, 64-bit. Use a fresh extracted folder with a supported Python installation.' }
$taskRequirements = Join-Path $PSScriptRoot 'requirements.txt'
$taskHash = (Get-FileHash -LiteralPath $taskRequirements -Algorithm SHA256).Hash
$taskMarker = Join-Path $PSScriptRoot '.venv\speech-review-requirements.sha256'
if (-not (Test-Path -LiteralPath $taskMarker) -or (Get-Content -LiteralPath $taskMarker -Raw).Trim() -ne $taskHash) {
    Write-Host 'Installing dependencies. The first run needs internet access; please wait...'
    & $taskPython -m pip install --upgrade pip --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'pip setup failed. Check your connection and run run.bat again.' }
    & $taskPython -m pip install -r $taskRequirements --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the error above and run run.bat again.' }
    Set-Content -LiteralPath $taskMarker -Value $taskHash -Encoding ascii
}
& $taskPython -c 'import tkinter,fastapi,uvicorn,av,ctranslate2,faster_whisper,pypinyin,praatio,multipart'
if ($LASTEXITCODE -ne 0) { throw 'A required dependency could not load. Check the error above.' }
if ($SetupOnly) { Write-Host 'Speech Review setup verified.'; exit 0 }
$taskPythonWindow = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
$taskLauncher = Join-Path $PSScriptRoot 'desktop\launcher.py'
Start-Process -FilePath $taskPythonWindow -ArgumentList @(('"' + $taskLauncher + '"'), '--home', ('"' + $PSScriptRoot + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
Write-Host 'Speech Review is starting. Keep its launcher window open while working.'
