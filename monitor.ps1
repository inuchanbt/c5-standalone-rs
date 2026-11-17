$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\James\AppData\Local\Python\pythoncore-3.14-64\python.exe'
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'tools\monitor.py') @args
exit $LASTEXITCODE
