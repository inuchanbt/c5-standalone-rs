$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\James\AppData\Local\Python\pythoncore-3.14-64\python.exe'
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'tools\probe_meter.py') @args
exit $LASTEXITCODE
