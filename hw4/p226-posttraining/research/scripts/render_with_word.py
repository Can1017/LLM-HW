"""Windows fallback when packaged render_docx cannot find LibreOffice."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
TITLE='大语言模型后训练演进与强化学习代码研究'
POPPLER=Path('C:/Users/86183/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
PWSH='C:/Program Files/PowerShell/7/pwsh.exe'

for suffix, directory in [('', 'qa-word-main'),('-附件','qa-word-appendix')]:
    src=ROOT/'reports'/(TITLE+suffix+'.docx')
    out=ROOT/'reports'/directory
    out.mkdir(exist_ok=True)
    pdf=out/(src.stem+'.pdf')
    script=f"""
$word = New-Object -ComObject Word.Application
$initialCount = $word.Documents.Count
$initialVisible = $word.Visible
$document = $null
try {{
    $word.Visible = $false
    $document = $word.Documents.Open('{src.as_posix()}',$false,$true)
    $document.ExportAsFixedFormat('{pdf.as_posix()}',17)
}} finally {{
    if ($null -ne $document) {{
        $document.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document)
    }}
    if ($initialCount -eq 0) {{ $word.Quit() }} else {{ $word.Visible = $initialVisible }}
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}}
"""
    subprocess.run([PWSH,'-NoLogo','-NoProfile','-Command',script],check=True)
    info=subprocess.check_output([str(POPPLER/'pdfinfo.exe'),str(pdf)],text=True,encoding='utf-8',errors='replace')
    print(src.name, [x for x in info.splitlines() if x.startswith(('Pages:','Page size:'))], flush=True)
    subprocess.run([str(POPPLER/'pdftoppm.exe'),'-png','-r','135',str(pdf),str(out/'page')],check=True)
