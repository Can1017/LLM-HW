"""Cache primary arXiv sources and extract searchable paper text."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / 'research' / 'papers'
PAPERS.mkdir(exist_ok=True)
IDS = ['2203.02155', '2305.18290', '2402.03300', '2412.19437',
       '2501.12948', '2503.14476', '2503.20783', '2505.09388',
       '2507.18071', '2512.02556', '2602.02276', '2602.15763', '2602.04879']


def fetch(paper_id):
    for suffix, route in [('html', 'abs'), ('pdf', 'pdf')]:
        target = PAPERS / f'{paper_id}.{suffix}'
        valid = target.exists() and target.stat().st_size > 2000
        if valid and suffix == 'pdf':
            try:
                len(PdfReader(target).pages)
            except Exception:
                valid = False
        if valid:
            continue
        part = target.with_suffix(target.suffix + '.part')
        subprocess.run(['curl', '-fL', '--max-time', '180', '-sS',
                        f'https://arxiv.org/{route}/{paper_id}', '-o', str(part)], check=True)
        if suffix == 'pdf':
            len(PdfReader(part).pages)
        part.replace(target)
    raw = (PAPERS / f'{paper_id}.html').read_text(encoding='utf-8')
    def meta(key):
        return [html.unescape(x) for x in re.findall(r'<meta name="'+key+r'" content="([^"]+)"', raw)]
    reader = PdfReader(PAPERS / f'{paper_id}.pdf')
    out = []
    for i, page in enumerate(reader.pages, 1):
        out.append(f'\n===== PDF PAGE {i} =====\n'+(page.extract_text() or ''))
    (PAPERS / f'{paper_id}.txt').write_text('\n'.join(out), encoding='utf-8')
    entry = dict(id=paper_id, title=meta('citation_title')[0], authors=meta('citation_author'),
                 first_date=meta('citation_date')[0], url=f'https://arxiv.org/abs/{paper_id}',
                 page_count=len(reader.pages), verified_on='2026-11-11',
                 pdf_sha256=hashlib.sha256((PAPERS/f'{paper_id}.pdf').read_bytes()).hexdigest())
    version = re.findall(r'arXiv:'+re.escape(paper_id)+r'v(\d+)', raw)
    entry['pdf_version'] = max(map(int, version)) if version else None
    print(json.dumps({k:v for k,v in entry.items() if k not in ('authors','pdf_sha256')}, ensure_ascii=False), flush=True)
    return entry


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=5) as ex:
        entries = list(ex.map(fetch, IDS))
    (ROOT/'research'/'references-verified.json').write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
