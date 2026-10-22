"""Shared character alignment, long-document windows and exact punctuation scores."""
from __future__ import annotations

import json
import time
import unicodedata
from pathlib import Path
import numpy as np

from prepare_data import ROOT, LABELS


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def article_runs(doc):
    """Join consecutive original paragraphs; quarantined/missing paragraphs split runs."""
    runs, text, labels, previous = [], '', [], None
    for p in doc['paragraphs']:
        number = int(p['id'].rsplit('-', 1)[1])
        if previous is not None and number != previous + 1:
            runs.append({'id': f"{doc['id']}-{previous}", 'text': text, 'labels': labels})
            text, labels = '', []
        text += p['text']
        labels.extend(p['labels'])
        previous = number
    if text:
        runs.append({'id': f"{doc['id']}-{previous}", 'text': text, 'labels': labels})
    return runs


def load_samples(split, corpus='news'):
    if corpus == 'cclue':
        return read_jsonl(ROOT / 'data/cclue' / f'{split}.jsonl')
    return [r for d in read_jsonl(ROOT / 'data/processed' / f'{split}.jsonl') for r in article_runs(d)]


def windows(length, width=400, stride=300):
    """Return (context start/end, owned start/end), partitioning every input position."""
    if not 0 < stride <= width:
        raise ValueError('Require 0 < stride <= width')
    starts = [0]
    while starts[-1] + width < length:
        starts.append(starts[-1] + stride)
    ends = [min(s + width, length) for s in starts]
    seams = [(ends[i] + starts[i + 1]) // 2 for i in range(len(starts) - 1)]
    boundaries = [0] + seams + [length]
    return [(s, e, boundaries[i], boundaries[i + 1]) for i, (s, e) in enumerate(zip(starts, ends))]


def encode_batch(tokenizer, texts, gold=None, owned=None):
    import torch
    # BERT normalizer removes control/private characters. Preserve their original
    # character position by representing them explicitly as the unknown token.
    characters = [[tokenizer.unk_token if unicodedata.category(c) in {'Co', 'Cf', 'Cc', 'Cs'} else c
                   for c in text] for text in texts]
    batch = tokenizer(characters, is_split_into_words=True,
                      padding=True, truncation=False, return_tensors='pt')
    if batch['input_ids'].shape[1] > 512:
        raise ValueError('Tokenized window exceeds 512 positions')
    positions, aligned = [], []
    for row, text in enumerate(texts):
        last = {}
        for j, char_id in enumerate(batch.word_ids(row)):
            if char_id is not None:
                last[char_id] = j
        if set(last) != set(range(len(text))):
            missing = [(i, repr(c)) for i, c in enumerate(text) if i not in last]
            raise ValueError(f'Tokenizer dropped input characters: {missing[:10]}')
        positions.append([last[i] for i in range(len(text))])
        if gold is not None:
            target = [-100] * batch['input_ids'].shape[1]
            lo, hi = owned[row] if owned else (0, len(text))
            for i in range(lo, hi):
                target[last[i]] = gold[row][i]
            aligned.append(target)
    model_inputs = dict(batch)
    if gold is not None:
        model_inputs['labels'] = torch.tensor(aligned, dtype=torch.long)
    return model_inputs, positions


def confusion_matrix(gold, predictions):
    gold, predictions = np.asarray(gold), np.asarray(predictions)
    valid = gold >= 0
    return np.bincount(8 * gold[valid] + predictions[valid], minlength=64).reshape(8, 8)


def scores(cm):
    cm = np.asarray(cm, dtype=np.int64)
    tp = cm.diagonal()
    predicted, actual = cm.sum(axis=0), cm.sum(axis=1)
    precision = np.divide(tp, predicted, out=np.zeros(8, dtype=float), where=predicted != 0)
    recall = np.divide(tp, actual, out=np.zeros(8, dtype=float), where=actual != 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros(8, dtype=float), where=precision + recall != 0)
    correct = int(tp[1:].sum())
    p, r = int(predicted[1:].sum()), int(actual[1:].sum())
    # A boundary is a full stop, question mark or exclamation mark.
    end = [2, 3, 4]
    boundary_tp = int(cm[np.ix_(end, end)].sum())
    boundary_p, boundary_r = int(predicted[end].sum()), int(actual[end].sum())
    return {
        'punctuation_micro_f1': 2 * correct / (p + r) if p + r else 0,
        'punctuation_macro_f1': float(f1[1:].mean()),
        'punctuation_precision': correct / p if p else 0,
        'punctuation_recall': correct / r if r else 0,
        'sentence_boundary_f1': 2 * boundary_tp / (boundary_p + boundary_r) if boundary_p + boundary_r else 0,
        'character_accuracy': float(tp.sum() / cm.sum()) if cm.sum() else 0,
        'scored_positions': int(cm.sum()), 'confusion_matrix': cm.tolist(),
        'per_class': {LABELS[i]: {'precision': float(precision[i]), 'recall': float(recall[i]),
                                 'f1': float(f1[i]), 'support': int(actual[i])} for i in range(8)}}


def restore(text, predictions):
    assert len(text) == len(predictions)
    return ''.join(c + (LABELS[int(i)] if i > 0 else '') for c, i in zip(text, predictions))


class Predictor:
    def __init__(self, checkpoint, precision='fp16'):
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        self.torch = torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.amp = precision == 'fp16' and self.device == 'cuda'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
        self.model = AutoModelForTokenClassification.from_pretrained(
            checkpoint, local_files_only=True, attn_implementation='sdpa').to(self.device).eval()
        self.timing = {}

    def predict_windows(self, texts):
        torch = self.torch
        began = time.perf_counter()
        inputs, positions = encode_batch(self.tokenizer, texts)
        self.timing['tokenization_seconds'] = self.timing.get('tokenization_seconds', 0.) + time.perf_counter() - began
        self.timing['forward_batches'] = self.timing.get('forward_batches', 0) + 1
        self.timing['largest_actual_batch'] = max(self.timing.get('largest_actual_batch', 0), len(texts))
        device_inputs = {k: v.to(self.device) for k, v in inputs.items()}
        if self.device == 'cuda':
            start_event = torch.cuda.Event(enable_timing=True)
            end_event = torch.cuda.Event(enable_timing=True)
            start_event.record()
        else:
            forward_start = time.perf_counter()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16, enabled=self.amp):
            logits = self.model(**device_inputs).logits
            if self.device == 'cuda':
                end_event.record()
            output = logits.argmax(-1).cpu().numpy()
        forward_seconds = (start_event.elapsed_time(end_event) / 1000 if self.device == 'cuda'
                           else time.perf_counter() - forward_start)
        self.timing['model_forward_seconds'] = self.timing.get('model_forward_seconds', 0.) + forward_seconds
        return [output[i, p].astype(np.int16) for i, p in enumerate(positions)]

    def fixed(self, samples, batch_size=4):
        result = [np.full(len(s['text']), -1, dtype=np.int16) for s in samples]
        tasks = [(i, w) for i, sample in enumerate(samples) for w in windows(len(sample['text']))]
        for b in range(0, len(tasks), batch_size):
            chunk = tasks[b:b + batch_size]
            output = self.predict_windows([samples[i]['text'][s:e] for i, (s, e, a, z) in chunk])
            for (i, (s, e, a, z)), pred in zip(chunk, output):
                result[i][a:z] = pred[a - s:z - s]
        assert all((p >= 0).all() for p in result)
        return result, len(tasks)

    def adaptive(self, samples, batch_size=1):
        # One ready window per document: batch across documents, never across dependencies.
        result = [np.full(len(s['text']), -1, dtype=np.int16) for s in samples]
        offsets = [0] * len(samples)
        calls = 0
        while True:
            active = [i for i, s in enumerate(samples) if offsets[i] < len(s['text'])]
            if not active:
                break
            for b in range(0, len(active), batch_size):
                chunk = active[b:b + batch_size]
                texts = [samples[i]['text'][offsets[i]:offsets[i] + 400] for i in chunk]
                predictions = self.predict_windows(texts)
                calls += len(chunk)
                for i, text, pred in zip(chunk, texts, predictions):
                    remaining = len(samples[i]['text']) - offsets[i]
                    if remaining <= 400:
                        take = remaining
                    else:
                        stops = np.flatnonzero(pred[:300] == 2)
                        take = int(stops[-1]) + 1 if len(stops) else 300
                    start = offsets[i]
                    result[i][start:start + take] = pred[:take]
                    offsets[i] += take
        assert all((p >= 0).all() for p in result)
        return result, calls
