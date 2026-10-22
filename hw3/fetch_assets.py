"""Fetch pinned pretrained weights and the published CCLUE files for HW3."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import requests

from prepare_data import ROOT, LABELS, write_json

MODEL_REVISION = '8f23c25b06e129b6c986331a13d8d025a92cf0ea'
CCLUE_REVISION = 'ed481c453c1c36397f86905a2bda625ecc5607e1'


def fetch(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        partial = destination.with_suffix(destination.suffix + '.partial')
        with requests.get(url, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            with partial.open('wb') as out:
                for chunk in response.iter_content(1024 * 1024):
                    out.write(chunk)
        partial.replace(destination)
    data = destination.read_bytes()
    record = {'url': url, 'path': str(destination.relative_to(ROOT)),
              'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    print(json.dumps(record, ensure_ascii=False), flush=True)
    return record


def parse_cclue(source, name):
    # Read the published CoNLL files directly; no execution of upstream dataset scripts.
    mapping = {'O': 0, 'B-,': 1, 'B-.': 2, 'B-?': 3, 'B-!': 4,
               'B-\\': 5, 'B-:': 6, 'B-;': 7}
    out_path = ROOT / 'data' / 'cclue' / f'{name}.jsonl'
    samples, chars, labels = [], [], []
    book, segment = 0, 0

    def flush():
        nonlocal chars, labels, segment
        if chars:
            samples.append({'id': f'cclue-{name}-{book}-{segment}',
                            'text': ''.join(chars), 'labels': labels})
            segment += 1
            chars, labels = [], []

    for line in source.read_text(encoding='utf-8').splitlines():
        if line.startswith('-DOCSTART-'):
            flush()
            book += 1
        elif not line.strip():
            flush()
        else:
            fields = line.split()
            assert len(fields) == 5, line
            assert len(fields[0]) == 1, fields[0]
            chars.append(fields[0])
            labels.append(mapping[fields[2]])
    flush()
    with out_path.open('w', encoding='utf-8', newline='\n') as out:
        for sample in samples:
            out.write(json.dumps(sample, ensure_ascii=False) + '\n')
    return {'samples': len(samples), 'characters': sum(len(s['text']) for s in samples),
            'over_400': sum(len(s['text']) > 400 for s in samples),
            'over_2000': sum(len(s['text']) > 2000 for s in samples)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('asset', choices=['model', 'cclue'])
    args = parser.parse_args()
    records = []
    if args.asset == 'model':
        for filename in ['config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.txt',
                         'README.md', 'model.safetensors']:
            records.append(fetch(
                f'https://huggingface.co/google-bert/bert-base-chinese/resolve/{MODEL_REVISION}/{filename}',
                ROOT / 'models' / 'bert-base-chinese' / filename))
        write_json(ROOT / 'results' / 'model_source.json', {
            'model': 'google-bert/bert-base-chinese', 'revision': MODEL_REVISION, 'files': records})
    else:
        base = f'https://raw.githubusercontent.com/Ethan-yt/CCLUE/{CCLUE_REVISION}'
        for name in ['README.md', 'LICENSE', 'data/clean_daizhige.ipynb', 'data/punctuation.ipynb',
                     'data/punctuation/punctuation.py', 'data/punctuation/dev.txt',
                     'data/punctuation/test.txt']:
            records.append(fetch(base + '/' + name, ROOT / 'data' / 'cclue' / 'upstream' / name))
        summary = {}
        for remote, local in [('dev', 'validation'), ('test', 'test')]:
            summary[local] = parse_cclue(ROOT / 'data/cclue/upstream/data/punctuation' / f'{remote}.txt', local)
        write_json(ROOT / 'results' / 'cclue_source.json', {
            'repository': 'https://github.com/Ethan-yt/CCLUE', 'revision': CCLUE_REVISION,
            'labels': LABELS, 'files': records, 'splits': summary,
            'upstream_processing': ['Simplified Chinese conversion', 'Selected symbol removal',
                'Require paragraph comma and full stop', 'Filter books by quote/book-mark counts',
                'Book-level split followed by 1% paragraph sampling'],
            'role': 'External transfer evaluation; no CCLUE training samples used.'})


if __name__ == '__main__':
    main()
