$ErrorActionPreference = 'Stop'
$documentPath = Join-Path $PSScriptRoot '高效率BERT古文断句标点微调与批量长文推理实验.docx'
$renderDirectory = Join-Path $PSScriptRoot '.qa\word'
New-Item -ItemType Directory -Path $renderDirectory -Force | Out-Null
$pdfPath = Join-Path $renderDirectory 'report.pdf'
$wordApplication = $null
$openedDocument = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    $openedDocument = $wordApplication.Documents.Open($documentPath, $false, $true)
    $openedDocument.Repaginate()
    $openedDocument.ExportAsFixedFormat($pdfPath, 17)
    [pscustomobject]@{Renderer='Microsoft Word COM'; Pages=$openedDocument.ComputeStatistics(2); PDF=$pdfPath} | ConvertTo-Json
} finally {
    if ($null -ne $openedDocument) { $openedDocument.Close(0) }
    if ($null -ne $wordApplication) { $wordApplication.Quit() }
}
$runtimePython = 'C:\Users\86183\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $runtimePython -c 'import fitz,sys,pathlib; doc=fitz.open(sys.argv[1]); out=pathlib.Path(sys.argv[2]); [(page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(out/f"page-{i+1}.png")) for i,page in enumerate(doc)]; print("Rendered",len(doc),"pages")' $pdfPath $renderDirectory
exit $LASTEXITCODE
