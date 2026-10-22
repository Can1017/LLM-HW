"""Evaluate full held-out corpora and benchmark measured long-document inference."""
from __future__ import annotations

import argparse
import json
import random
import time

import numpy as np
import torch

from prepare_data import ROOT, write_json
from core import Predictor, confusion_matrix, load_samples, restore, scores, windows


def aggregate(samples, predictions, seam_radius=None):
    cm = np.zeros((8, 8), dtype=np.int64)
    for sample, prediction in zip(samples, predictions):
        gold = np.asarray(sample['labels'])
        if seam_radius is not None:
            selected = np.zeros(len(gold), dtype=bool)
            ws = windows(len(gold))
            for _, _, _, seam in ws[:-1]:
                selected[max(0, seam - seam_radius):min(len(gold), seam + seam_radius)] = True
            gold = np.where(selected, gold, -100)
        cm += confusion_matrix(gold, prediction)
    return scores(cm)


def timed_predict(predictor, samples, strategy, batch_size):
    predictor.timing = {}
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
    start = time.perf_counter()
    predictions, window_count = getattr(predictor, strategy)(samples, batch_size)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    return predictions, {
        'strategy': strategy, 'batch_size': batch_size, 'seconds': elapsed,
        'windows': window_count, 'documents_or_segments': len(samples),
        'original_characters': sum(len(s['text']) for s in samples),
        'characters_per_second': sum(len(s['text']) for s in samples) / elapsed,
        **predictor.timing,
        'allocated_peak_mib': torch.cuda.max_memory_allocated() / 2**20 if torch.cuda.is_available() else None,
        'reserved_peak_mib': torch.cuda.max_memory_reserved() / 2**20 if torch.cuda.is_available() else None}


def evaluate(args):
    predictor = Predictor(ROOT / 'models' / args.run)
    records = []
    for corpus in ['news', 'cclue']:
        samples = load_samples('test', corpus)
        gold = [y for s in samples for y in s['labels']]
        none = confusion_matrix(gold, np.zeros(len(gold), dtype=np.int16))
        strategies = [('adaptive', 1), ('adaptive', args.batch), ('fixed', 1), ('fixed', args.batch)]
        fixed_baseline = None
        for strategy, batch in strategies:
            predictor.predict_windows([samples[0]['text'][:400]])
            predictions, record = timed_predict(predictor, samples, strategy, batch)
            record.update(corpus=corpus, metrics=aggregate(samples, predictions),
                          seam_metrics=aggregate(samples, predictions, 20))
            if strategy == 'fixed' and batch == 1:
                fixed_baseline = predictions
            elif strategy == 'fixed':
                record['different_labels_from_fixed_batch1'] = sum(
                    int((a != b).sum()) for a, b in zip(fixed_baseline, predictions))
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            if strategy == 'fixed' and batch == args.batch:
                save_predictions(args.run, corpus, samples, predictions)
            write_json(ROOT / 'results' / f'{args.run}_evaluation.json', {
                'checkpoint_record': json.loads((ROOT / 'models' / args.run / 'training_record.json').read_text()),
                'precision': 'fp16', 'experiments': records})
        write_json(ROOT / 'results' / f'{corpus}_none_baseline.json', scores(none))


def save_predictions(run, corpus, samples, predictions):
    folder = ROOT / 'data' / 'predictions' / run
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f'{corpus}.jsonl').open('w', encoding='utf-8', newline='\n') as out:
        for sample, prediction in zip(samples, predictions):
            out.write(json.dumps({**sample, 'predictions': prediction.tolist()}, ensure_ascii=False) + '\n')
    # Deterministic examples: length-selected, rare-mark and lowest-scoring examples.
    selected = []
    selected.append(('first_medium', next(i for i, s in enumerate(samples) if 80 <= len(s['text']) <= 200)))
    selected.append(('first_question', next(i for i, s in enumerate(samples) if 3 in s['labels'])))
    selected.append(('longest', max(range(len(samples)), key=lambda i: len(samples[i]['text']))))
    eligible = [i for i, s in enumerate(samples) if 80 <= len(s['text']) <= 400
                and sum(y > 0 for y in s['labels']) >= 5]
    selected.append(('lowest_f1_medium', min(eligible, key=lambda i: aggregate([samples[i]], [predictions[i]])['punctuation_micro_f1'])))
    examples = []
    for reason, i in selected:
        sample, prediction = samples[i], predictions[i]
        gold = sample['labels']
        examples.append({'selection': reason, 'id': sample['id'], 'characters': len(sample['text']),
                         'input': sample['text'], 'reference': restore(sample['text'], gold),
                         'prediction': restore(sample['text'], prediction),
                         'input_prefix': sample['text'][:350],
                         'reference_prefix': restore(sample['text'][:350], gold[:350]),
                         'prediction_prefix': restore(sample['text'][:350], prediction[:350]),
                         'seam_excerpts': [{'seam_offset': seam,
                                           'input': sample['text'][max(0, seam-40):seam+40],
                                           'reference': restore(sample['text'][max(0, seam-40):seam+40],
                                                                gold[max(0, seam-40):seam+40]),
                                           'prediction': restore(sample['text'][max(0, seam-40):seam+40],
                                                                 prediction[max(0, seam-40):seam+40])}
                                          for _, _, _, seam in windows(len(sample['text']))[:-1]][:3],
                         'ignored_positions': [j for j, label in enumerate(gold) if label < 0],
                         'metrics': aggregate([sample], [prediction]),
                         'errors': [{'offset': j, 'gold': gold[j], 'prediction': int(prediction[j]),
                                     'context': sample['text'][max(0, j - 12):j + 13]}
                                    for j in range(len(gold)) if gold[j] >= 0 and gold[j] != prediction[j]]})
    write_json(ROOT / 'results' / f'{run}_{corpus}_examples.json', examples)


def benchmark(args):
    predictor = Predictor(ROOT / 'models' / args.run)
    samples = load_samples('test')
    candidates = [s for s in samples if len(s['text']) >= 2000]
    random.Random(42).shuffle(candidates)
    multiple = candidates[:24]
    single = [max(candidates, key=lambda s: len(s['text']))]
    records = []
    tasks = [('single_long_document', single), ('multiple_long_documents', multiple)]
    for workload, batch_samples in tasks:
        input_hash = __import__('hashlib').sha256(''.join(s['text'] for s in batch_samples).encode()).hexdigest()
        for strategy, batches in [('adaptive', [1, 4, 8, 16]), ('fixed', [1, 2, 4, 8, 16, 32])]:
            for batch in batches:
                torch.cuda.empty_cache()
                try:
                    predictor.predict_windows([s['text'][:400] for s in batch_samples[:min(batch, len(batch_samples))]])
                    repetitions = []
                    for repeat in range(5):
                        prediction, record = timed_predict(predictor, batch_samples, strategy, batch)
                        record.update(workload=workload, repeat=repeat, input_sha256=input_hash,
                                      metrics=aggregate(batch_samples, prediction),
                                      seam_metrics=aggregate(batch_samples, prediction, 20))
                        repetitions.append(record)
                    records.extend(repetitions)
                    median = float(np.median([r['seconds'] for r in repetitions]))
                    print(json.dumps({'workload': workload, 'strategy': strategy, 'batch': batch,
                                      'median_seconds': median,
                                      'characters': sum(len(s['text']) for s in batch_samples)}, ensure_ascii=False), flush=True)
                except torch.cuda.OutOfMemoryError as exc:
                    records.append({'workload': workload, 'strategy': strategy, 'batch_size': batch,
                                    'status': 'cuda_oom', 'message': str(exc)[:400]})
                    torch.cuda.empty_cache()
                    break
                write_json(ROOT / 'results' / f'{args.run}_benchmark.json', {
                    'gpu': torch.cuda.get_device_name(0), 'precision': 'fp16',
                    'timing_scope': 'tokenization, CPU/GPU transfer, forward, argmax and stitching; model loading excluded',
                    'records': records,
                    'inputs': {name: [{'id': s['id'], 'characters': len(s['text'])} for s in data]
                               for name, data in tasks}})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['evaluate', 'benchmark'])
    parser.add_argument('--run', default='news-bert')
    parser.add_argument('--batch', type=int, default=8)
    args = parser.parse_args()
    torch.set_num_threads(4)
    if args.mode == 'evaluate':
        evaluate(args)
    else:
        benchmark(args)
