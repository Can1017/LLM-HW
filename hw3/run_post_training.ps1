$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
Set-Location -LiteralPath $experimentRoot
$condaExe = (Get-Command conda.exe -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath 'results\news-bert_completion.json')) {
    throw 'Wait for the active training process to finish before running evaluation.'
}
& $condaExe run --no-capture-output -n hw3-bert python -u evaluate.py evaluate --batch 8 *> logs\news-bert\evaluation.log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $condaExe run --no-capture-output -n hw3-bert python -u evaluate.py benchmark *> logs\news-bert\benchmark.log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $condaExe run --no-capture-output -n hw3-bert python -u evaluate_lunyu.py *> logs\news-bert\lunyu.log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $condaExe run --no-capture-output -n hw3-bert python build_report.py
exit $LASTEXITCODE
