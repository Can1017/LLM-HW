"""Prepare HW3 punctuation labels directly from the supplied archive."""
from __future__ import annotations

import collections
import hashlib
import json
import random
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parent / 'hw2' / '1998-上半年-带音.rar'
LABELS = ['NONE', '，', '。', '？', '！', '、', '：', '；']
IDS = re.compile(r'^(\d{8}-\d{2}-\d{3})-(\d{3})\s+(.*)$')
PRON = re.compile(r'\{[A-Za-züÜvV0-9 :]+\}')
REMOVED = set('“”‘’「」『』（）()《》〈〉【】[]〔〕［］｛｝"')
AMBIGUOUS = set('—…─')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def clean(body, counts):
    counts['pronunciation_spans'] += len(PRON.findall(body))
    body = PRON.sub('', body)
    if '{' in body or '}' in body:
        raise ValueError(f'Unrecognized brace annotation: {body[:160]}')
    chars, labels, ignored = [], [], set()
    for c in body:
        if c.isspace():
            counts['segmentation_whitespace'] += 1
            continue
        if c in LABELS[1:]:
            counts['target_' + c] += 1
            if not chars:
                counts['leading_target_marks'] += 1
            elif labels[-1] != 0:
                ignored.add(len(chars) - 1)
                counts['multiple_target_marks_at_gap'] += 1
            else:
                labels[-1] = LABELS.index(c)
            continue
        if c in REMOVED or c in AMBIGUOUS:
            counts['excluded_' + c] += 1
            if c in AMBIGUOUS and chars:
                ignored.add(len(chars) - 1)
            continue
        if ord(c) < 32 or c == '\ufffd':
            raise ValueError(f'Unexpected control/replacement character: {c!r}')
        # Narrow normalization preserves punctuation distinctions and original words.
        if '０' <= c <= '９':
            counts['fullwidth_digits_normalized'] += 1
            c = chr(ord(c) - ord('０') + ord('0'))
        chars.append(c)
        labels.append(0)
    for i in ignored:
        labels[i] = -100
    counts['ignored_gaps'] += len(ignored)
    return ''.join(chars), labels


def prepare(archive=ARCHIVE):
    data = ROOT / 'data'
    processed = data / 'processed'
    processed.mkdir(parents=True, exist_ok=True)
    before_hash = digest(archive.read_bytes())
    stats, quarantined, documents = [], [], []
    for month in range(1, 7):
        raw = subprocess.check_output([
            'C:/Windows/System32/tar.exe', '-xOf', str(archive), f'*1998-{month:02d}*'])
        counts = collections.Counter()
        docs = {}
        for line_number, raw_line in enumerate(raw.splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                line = raw_line.decode('gb18030', errors='strict')
            except UnicodeDecodeError as exc:
                quarantined.append({
                    'month': month, 'line': line_number,
                    'paragraph_id': raw_line.split(b' ', 1)[0].decode('ascii'),
                    'reason': str(exc), 'original_bytes_hex': raw_line.hex(),
                    'original_sha256': digest(raw_line)})
                counts['quarantined_paragraphs'] += 1
                continue
            match = IDS.fullmatch(line)
            if match is None:
                raise ValueError(f'Unexpected record format: month={month}, line={line_number}')
            article, paragraph, body = match.groups()
            counts['raw_valid_paragraphs'] += 1
            doc = docs.setdefault(article, {'id': article, 'month': month, 'paragraphs': []})
            chars, labels = clean(body, counts)
            if chars:
                assert len(chars) == len(labels)
                doc['paragraphs'].append({'id': article + '-' + paragraph,
                                           'text': chars, 'labels': labels})
        documents.extend(d for d in docs.values() if d['paragraphs'])
        stats.append({'month': month, 'file_bytes': len(raw), 'sha256': digest(raw),
                      'raw_article_ids': len(docs), 'counts': dict(counts)})

    # Identical unpunctuated documents share a group, including cross-month copies.
    groups = collections.defaultdict(list)
    for doc in documents:
        content = ''.join(p['text'] for p in doc['paragraphs'])
        doc['content_sha256'] = digest(content.encode('utf-8'))
        groups[doc['content_sha256']].append(doc)
    months = collections.defaultdict(list)
    for key, group in groups.items():
        months[group[0]['month']].append(key)
    splits = {name: [] for name in ['train', 'validation', 'test']}
    for month, keys in sorted(months.items()):
        keys.sort()
        random.Random(42 + month).shuffle(keys)
        n_train, n_valid = int(len(keys) * .8), int(len(keys) * .1)
        for i, key in enumerate(keys):
            name = 'train' if i < n_train else 'validation' if i < n_train + n_valid else 'test'
            # Keep one exact document; record all duplicate source identities.
            doc = groups[key][0]
            doc['duplicate_ids'] = [d['id'] for d in groups[key][1:]]
            splits[name].append(doc)
    summary = {}
    for name, docs in splits.items():
        docs.sort(key=lambda d: d['id'])
        with (processed / f'{name}.jsonl').open('w', encoding='utf-8', newline='\n') as out:
            for doc in docs:
                out.write(json.dumps(doc, ensure_ascii=False) + '\n')
        labels = collections.Counter(label for d in docs for p in d['paragraphs'] for label in p['labels'])
        summary[name] = {
            'articles': len(docs), 'paragraphs': sum(len(d['paragraphs']) for d in docs),
            'characters': sum(len(p['text']) for d in docs for p in d['paragraphs']),
            'labels': {('IGNORE' if i == -100 else LABELS[i]): n for i, n in sorted(labels.items())},
            'paragraphs_over_400': sum(len(p['text']) > 400 for d in docs for p in d['paragraphs']),
            'paragraphs_over_2000': sum(len(p['text']) > 2000 for d in docs for p in d['paragraphs']),
            'split_sha256': digest('\n'.join(d['id'] for d in docs).encode())}
    hashes = [{d['content_sha256'] for d in docs} for docs in splits.values()]
    assert not any(hashes[i] & hashes[j] for i in range(3) for j in range(i))
    assert digest(archive.read_bytes()) == before_hash
    assert len(quarantined) == 5
    write_json(data / 'quarantine.json', quarantined)
    write_json(ROOT / 'results' / 'data_statistics.json', {
        'archive': str(archive), 'archive_sha256': before_hash, 'seed': 42,
        'labels': LABELS, 'sources': stats, 'splits': summary,
        'duplicate_articles_removed': len(documents) - len(groups),
        'quarantined_paragraphs': [{k: q[k] for k in ['paragraph_id', 'month', 'line', 'original_sha256']}
                                    for q in quarantined]})
    examples = []
    for name, docs in splits.items():
        for doc in docs:
            candidates = [p for p in doc['paragraphs'] if 50 <= len(p['text']) <= 180
                          and all(i >= 0 for i in p['labels'])]
            if candidates:
                p = candidates[0]
                examples.append({'split': name, **p, 'reconstructed_target': ''.join(
                    c + (LABELS[i] if i > 0 else '') for c, i in zip(p['text'], p['labels']))})
                break
    write_json(ROOT / 'results' / 'label_examples.json', examples)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=ARCHIVE, help='Path to the supplied six-month RAR archive')
    prepare(parser.parse_args().archive)
