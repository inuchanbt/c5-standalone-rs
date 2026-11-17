$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\James\AppData\Local\Python\pythoncore-3.14-64\python.exe'
& $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'tools\gated_monitor.py') @args
exit $LASTEXITCODE
