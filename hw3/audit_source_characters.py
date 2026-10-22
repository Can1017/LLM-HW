"""Record original-source evidence for the two unusual characters in report examples."""
import hashlib
import json
from pathlib import Path
import subprocess
import unicodedata

from prepare_data import ARCHIVE, ROOT, write_json


def main():
    statistics = json.loads((ROOT / 'results/data_statistics.json').read_text(encoding='utf-8'))
    archive_path = Path(statistics['archive'])
    raw = subprocess.check_output(['C:/Windows/System32/tar.exe', '-xOf', str(archive_path), '*1998-03*'])
    line = next(line for line in raw.splitlines() if line.startswith(b'19980304-02-002-001 '))
    decoded = line.decode('gb18030', 'strict')
    assert '〓' in decoded and '〓'.encode('gb18030').hex() == 'a1fe'
    source = ROOT / 'data/cclue/upstream/data/punctuation/test.txt'
    rows = source.read_text(encoding='utf-8').splitlines()
    i = next(i for i, value in enumerate(rows) if '\ue583' in value)
    write_json(ROOT / 'results/source_character_audit.json', {
        'news': {'paragraph_id': '19980304-02-002-001', 'original_line': decoded,
                 'line_sha256': hashlib.sha256(line).hexdigest(),
                 'codepoint': 'U+3013', 'unicode_name': unicodedata.name('〓'),
                 'source_encoding': 'gb18030', 'source_bytes_hex': 'a1fe',
                 'meaning': 'GETA MARK; used as a missing/unrepresentable character placeholder; intended original title character unconfirmed'},
        'cclue': {'source_url': 'https://raw.githubusercontent.com/Ethan-yt/CCLUE/ed481c453c1c36397f86905a2bda625ecc5607e1/data/punctuation/test.txt',
                  'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                  'source_line_number': i + 1, 'source_rows': rows[i-8:i+9],
                  'codepoint': 'U+E583', 'unicode_category': unicodedata.category('\ue583'),
                  'meaning': 'Private-use character; no universal glyph/meaning without the originating font or mapping'},
        'presentation': 'Yellow square at the original position, with codepoint caption. Original stored inputs, labels and model weights preserved.'})


if __name__ == '__main__':
    main()
