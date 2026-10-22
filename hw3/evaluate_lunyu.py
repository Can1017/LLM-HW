"""Evaluate the unchanged news model on a pinned, source-traceable Analects text."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import torch

from core import Predictor, load_samples, restore
from evaluate import aggregate, timed_predict
from fetch_assets import fetch
from prepare_data import ROOT, LABELS, clean, write_json

REVISION = 'b8594f81a89752241442f2ce267d6f66f96704ee'
BASE = f'https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/{REVISION}/'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    source = ROOT / 'data/lunyu/upstream'
    records = [fetch(BASE + remote, source / name) for remote, name in [
        ('论语/lunyu.json', 'lunyu.json'), ('论语/README.md', 'README.md'), ('LICENSE', 'LICENSE')]]
    chapters = json.loads((source / 'lunyu.json').read_text(encoding='utf-8'))
    assert len(chapters) == 20
    counts, paragraphs, whole_chapters = Counter(), [], []
    # Record mappings for the three ASCII punctuation types in this edition.
    punctuation_map = {',': '，', '?': '？', ':': '：'}
    for ci, chapter in enumerate(chapters, 1):
        chapter_rows = []
        for pi, original in enumerate(chapter['paragraphs'], 1):
            for c in original:
                if c in punctuation_map:
                    counts[f'ascii_{ord(c)}_mapped'] += 1
            mapped = ''.join(punctuation_map.get(c, c) for c in original)
            text, labels = clean(mapped, counts)
            assert text and len(text) == len(labels)
            unusual = [c for c in text if not '\u3400' <= c <= '\u9fff']
            assert not unusual, unusual
            row = {'id': f'lunyu-{ci:02d}-{pi:03d}', 'chapter': chapter['chapter'],
                   'original': original, 'text': text, 'labels': labels}
            paragraphs.append(row)
            chapter_rows.append(row)
        whole_chapters.append({'id': f'lunyu-{ci:02d}', 'chapter': chapter['chapter'],
                               'text': ''.join(r['text'] for r in chapter_rows),
                               'labels': [y for r in chapter_rows for y in r['labels']]})
    assert len(paragraphs) == 512
    out = ROOT / 'data/lunyu'
    for name, rows in [('paragraphs', paragraphs), ('chapters', whole_chapters)]:
        with (out / f'{name}.jsonl').open('w', encoding='utf-8', newline='\n') as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    # Diagnose verbatim quotation exposure in supervised news fine-tuning data.
    news = load_samples('train')
    overlaps = []
    for row in paragraphs:
        match = next((s['id'] for s in news if row['text'] in s['text']), None)
        if match is not None:
            overlaps.append({'lunyu_id': row['id'], 'news_training_id': match,
                             'characters': len(row['text'])})
    labels = Counter(y for row in paragraphs for y in row['labels'])
    manifest = {'repository': 'https://github.com/chinese-poetry/chinese-poetry',
                'revision': REVISION, 'files': records,
                'source_role': 'Pinned open-source electronic Analects punctuation reference',
                'upstream_readme_discrepancies': ['README: traditional; current JSON: simplified',
                                                  'README: 492 chapters/sections; JSON: 512 records in 20 books'],
                'punctuation_normalization': punctuation_map,
                'processing_counts': dict(counts), 'paragraphs': len(paragraphs),
                'chapters': len(whole_chapters), 'characters': sum(len(r['text']) for r in paragraphs),
                'paragraph_max_characters': max(len(r['text']) for r in paragraphs),
                'chapter_max_characters': max(len(r['text']) for r in whole_chapters),
                'chapter_over_400': sum(len(r['text']) > 400 for r in whole_chapters),
                'chapter_over_510': sum(len(r['text']) > 510 for r in whole_chapters),
                'label_counts': {('IGNORE' if i < 0 else LABELS[i]): n for i, n in sorted(labels.items())},
                'verbatim_news_training_quotations': overlaps,
                'reference_crosscheck': {'url': 'https://ctext.org/analects/xue-er/zhs',
                    'scope': 'Read-only spot check of opening passages; no wholesale text or punctuation replacement',
                    'observations': ['Opening Analects passage agrees',
                                     'Second passage has a comma difference after 不好犯上 in the two electronic editions']},
                'role': 'Evaluation only; no new model training or hyperparameter selection',
                'interpretation': 'Agreement with a fixed electronic punctuation edition; common classics may occur in pretraining.'}
    write_json(ROOT / 'results/lunyu_source.json', manifest)
    return paragraphs, whole_chapters, manifest


def main():
    torch.set_num_threads(4)
    paragraphs, chapters, source = prepare()
    checkpoint = ROOT / 'models/news-bert/model.safetensors'
    before = sha(checkpoint)
    predictor = Predictor(checkpoint.parent)
    experiments, saved = [], {}
    for granularity, samples in [('paragraphs', paragraphs), ('chapters', chapters)]:
        for strategy, batch in [('fixed', 1), ('fixed', 8), ('adaptive', 1), ('adaptive', 8)]:
            predictor.predict_windows([samples[0]['text'][:400]])
            predictions, record = timed_predict(predictor, samples, strategy, batch)
            record.update(granularity=granularity, metrics=aggregate(samples, predictions))
            if granularity == 'chapters':
                record['seam_metrics'] = aggregate(samples, predictions, 20)
            experiments.append(record)
            print(granularity, strategy, batch, record['metrics']['punctuation_micro_f1'], flush=True)
            if strategy == 'fixed' and batch == 8:
                saved[granularity] = predictions
                path = ROOT / 'data/predictions/news-bert' / f'lunyu_{granularity}.jsonl'
                with path.open('w', encoding='utf-8', newline='\n') as out:
                    for row, prediction in zip(samples, predictions):
                        out.write(json.dumps({**row, 'predictions': prediction.tolist()}, ensure_ascii=False) + '\n')
    overlapped = {r['lunyu_id'] for r in source['verbatim_news_training_quotations']}
    selected = [i for i, row in enumerate(paragraphs) if row['id'] not in overlapped]
    sensitivity = aggregate([paragraphs[i] for i in selected], [saved['paragraphs'][i] for i in selected])
    per_chapter = []
    for row, prediction in zip(chapters, saved['chapters']):
        per_chapter.append({'id': row['id'], 'chapter': row['chapter'], 'characters': len(row['text']),
                            'metrics': aggregate([row], [prediction])})
    # Retain the familiar opening, a medium passage and the lowest-F1 eligible passage.
    eligible = [i for i, row in enumerate(paragraphs) if len(row['text']) >= 30
                and sum(y > 0 for y in row['labels']) >= 5]
    choices = [('opening', 0), ('longest', max(range(len(paragraphs)), key=lambda i: len(paragraphs[i]['text']))),
               ('lowest_f1', min(eligible, key=lambda i: aggregate([paragraphs[i]], [saved['paragraphs'][i]])['punctuation_micro_f1']))]
    examples = []
    for reason, i in choices:
        row, prediction = paragraphs[i], saved['paragraphs'][i]
        examples.append({'selection': reason, **row,
                         'reference': restore(row['text'], row['labels']),
                         'prediction': restore(row['text'], prediction),
                         'metrics': aggregate([row], [prediction])})
    assert sha(checkpoint) == before
    write_json(ROOT / 'results/news-bert_lunyu.json', {
        'checkpoint_sha256_before': before, 'checkpoint_sha256_after': sha(checkpoint),
        'precision': 'fp16', 'experiments': experiments, 'per_chapter': per_chapter,
        'supervised_quotation_sensitivity': {'excluded_verbatim_paragraphs': len(overlapped),
                                           'remaining_paragraphs': len(selected), 'metrics': sensitivity},
        'examples': examples, 'training': 'No additional training performed'})


if __name__ == '__main__':
    main()
