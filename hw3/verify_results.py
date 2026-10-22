"""Recompute held-out metrics from saved predictions and verify the completed run."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from core import load_samples, read_jsonl, confusion_matrix, scores
from prepare_data import ROOT, ARCHIVE, write_json


def main():
    read = lambda name: json.loads((ROOT / 'results' / name).read_text(encoding='utf-8'))
    data = read('data_statistics.json')
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == data['archive_sha256']
    seen_ids, seen_content = set(), set()
    for split in ['train', 'validation', 'test']:
        docs = read_jsonl(ROOT / 'data/processed' / f'{split}.jsonl')
        ids = {d['id'] for d in docs}
        content = {hashlib.sha256(''.join(p['text'] for p in d['paragraphs']).encode()).hexdigest() for d in docs}
        assert not ids & seen_ids and not content & seen_content
        assert len(docs) == data['splits'][split]['articles']
        seen_ids |= ids
        seen_content |= content
    assert len(json.loads((ROOT / 'data/quarantine.json').read_text(encoding='utf-8'))) == 5
    completion, history = read('news-bert_completion.json'), read('news-bert_history.json')
    assert completion['epochs_completed'] == 3
    assert [r['epoch'] for r in history] == [1, 2, 3]
    assert completion['optimizer_steps'] == history[-1]['optimizer_step'] == 6237
    checkpoint = json.loads((ROOT / 'models/news-bert/training_record.json').read_text(encoding='utf-8'))
    assert checkpoint['epoch'] == max(history, key=lambda r: r['validation']['punctuation_micro_f1'])['epoch']
    evaluation = read('news-bert_evaluation.json')
    assert len(evaluation['experiments']) == 8
    verified = {}
    for corpus in ['news', 'cclue']:
        source = load_samples('test', corpus)
        saved = read_jsonl(ROOT / 'data/predictions/news-bert' / f'{corpus}.jsonl')
        assert len(source) == len(saved)
        cm = np.zeros((8, 8), dtype=np.int64)
        for original, prediction in zip(source, saved):
            for field in ['id', 'text', 'labels']:
                assert original[field] == prediction[field]
            assert len(original['text']) == len(prediction['predictions'])
            assert all(0 <= x < 8 for x in prediction['predictions'])
            cm += confusion_matrix(original['labels'], prediction['predictions'])
        stored = next(r for r in evaluation['experiments']
                      if r['corpus'] == corpus and r['strategy'] == 'fixed' and r['batch_size'] == 8)
        assert cm.tolist() == stored['metrics']['confusion_matrix']
        recomputed = scores(cm)
        assert recomputed['punctuation_micro_f1'] == stored['metrics']['punctuation_micro_f1']
        assert recomputed['scored_positions'] == sum(y >= 0 for s in source for y in s['labels'])
        verified[corpus] = {'samples': len(source), 'scored_positions': recomputed['scored_positions'],
                            'recomputed_micro_f1': recomputed['punctuation_micro_f1']}
    benchmark = read('news-bert_benchmark.json')
    groups = Counter((r['workload'], r['strategy'], r['batch_size']) for r in benchmark['records'])
    assert len(groups) == 20 and set(groups.values()) == {5}
    for r in benchmark['records']:
        assert r['seconds'] > 0
        if r['workload'] == 'single_long_document' and r['strategy'] == 'adaptive':
            assert r['largest_actual_batch'] == 1
    (ROOT / '作业报告.md').read_text(encoding='utf-8')
    figures = list((ROOT / 'figures').glob('*.png'))
    assert len(figures) == 10
    example_figures = json.loads((ROOT / 'results/example_figures.json').read_text(encoding='utf-8'))
    assert len(example_figures) == 12
    assert all((ROOT / r['path']).is_file() for r in example_figures.values())
    lunyu = read('news-bert_lunyu.json')
    provenance = read('lunyu_source.json')
    checkpoint_sha256 = hashlib.sha256((ROOT / 'models/news-bert/model.safetensors').read_bytes()).hexdigest()
    assert lunyu['checkpoint_sha256_before'] == lunyu['checkpoint_sha256_after'] == checkpoint_sha256
    assert len(lunyu['experiments']) == 8
    for file in provenance['files']:
        assert hashlib.sha256((ROOT / file['path']).read_bytes()).hexdigest() == file['sha256']
    for granularity, count in [('paragraphs', 512), ('chapters', 20)]:
        source = read_jsonl(ROOT / 'data/lunyu' / f'{granularity}.jsonl')
        saved = read_jsonl(ROOT / 'data/predictions/news-bert' / f'lunyu_{granularity}.jsonl')
        assert len(source) == len(saved) == count
        cm = np.zeros((8, 8), dtype=np.int64)
        for original, prediction in zip(source, saved):
            for field in ['id', 'text', 'labels']:
                assert original[field] == prediction[field]
            assert len(original['text']) == len(prediction['predictions'])
            assert all(0 <= x < 8 for x in prediction['predictions'])
            cm += confusion_matrix(original['labels'], prediction['predictions'])
        stored = next(r for r in lunyu['experiments'] if r['granularity'] == granularity
                      and r['strategy'] == 'fixed' and r['batch_size'] == 8)
        assert cm.tolist() == stored['metrics']['confusion_matrix']
        assert scores(cm)['scored_positions'] == 15915
        verified['lunyu_' + granularity] = {'samples': count, 'scored_positions': int(cm.sum()),
                                           'recomputed_micro_f1': scores(cm)['punctuation_micro_f1']}
    result = {'status': 'passed', 'archive_unchanged': True, 'disjoint_article_splits': True,
              'epochs_completed': 3, 'optimizer_steps': 6237, 'checkpoint_epoch': checkpoint['epoch'],
              'prediction_metrics_recomputed': verified, 'benchmark_configurations': len(groups),
              'repeats_per_configuration': 5, 'figures': len(figures), 'example_figures': len(example_figures),
              'unchanged_news_checkpoint_after_lunyu': True}
    write_json(ROOT / 'results/verification.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
