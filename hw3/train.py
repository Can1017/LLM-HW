"""Full BERT fine-tuning, aligned-window cache and measured CUDA feasibility run."""
from __future__ import annotations

import argparse
import json
import math
import random
import time

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification, get_linear_schedule_with_warmup

from prepare_data import ROOT, LABELS, write_json
from core import load_samples, windows, encode_batch, scores

PRETRAINED = ROOT / 'models/bert-base-chinese'


def seed_all():
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
    torch.set_num_threads(4)


def cache(split):
    target = ROOT / 'data/cache' / f'{split}.pt'
    if target.exists():
        return torch.load(target, weights_only=True)
    tokenizer = AutoTokenizer.from_pretrained(PRETRAINED, local_files_only=True)
    samples = load_samples(split)
    tasks = [(s, w) for s in samples for w in windows(len(s['text']))]
    rows, supervised, unknown = [], 0, 0
    for b in range(0, len(tasks), 128):
        chunk = tasks[b:b + 128]
        texts = [s['text'][a:z] for s, (a, z, lo, hi) in chunk]
        gold = [s['labels'][a:z] for s, (a, z, lo, hi) in chunk]
        owned = [(lo - a, hi - a) for s, (a, z, lo, hi) in chunk]
        inputs, _ = encode_batch(tokenizer, texts, gold, owned)
        for j in range(len(chunk)):
            n = int(inputs['attention_mask'][j].sum())
            row = {k: v[j, :n].clone() for k, v in inputs.items()}
            supervised += int((row['labels'] >= 0).sum())
            unknown += int((row['input_ids'] == tokenizer.unk_token_id).sum())
            rows.append(row)
        if b % 4096 == 0:
            print('TOKENIZED', split, min(b + 128, len(tasks)), '/', len(tasks), flush=True)
    expected = sum(sum(y >= 0 for y in s['labels']) for s in samples)
    assert supervised == expected, (supervised, expected)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(rows, target)
    write_json(ROOT / 'results' / f'{split}_alignment.json', {
        'samples': len(samples), 'windows': len(rows), 'supervised_characters': supervised,
        'expected_supervised_characters': expected, 'unknown_tokens_including_overlap': unknown,
        'max_token_length': max(len(r['input_ids']) for r in rows),
        'context_characters': 400, 'stride_characters': 300,
        'overlap_loss': 'Only the owned core of each window contributes to loss/metrics.'})
    return rows


def collate(rows):
    length = max(len(r['input_ids']) for r in rows)
    result = {}
    for key in rows[0]:
        tensor = torch.full((len(rows), length), -100 if key == 'labels' else 0, dtype=torch.long)
        for i, row in enumerate(rows):
            tensor[i, :len(row[key])] = row[key]
        result[key] = tensor
    return result


def init_model():
    return AutoModelForTokenClassification.from_pretrained(
        PRETRAINED, num_labels=8, id2label=dict(enumerate(LABELS)),
        label2id={s: i for i, s in enumerate(LABELS)},
        local_files_only=True, attn_implementation='sdpa')


@torch.inference_mode()
def evaluate(model, rows, batch_size, device):
    model.eval()
    cm = np.zeros((8, 8), dtype=np.int64)
    total_loss, positions = 0., 0
    for batch in DataLoader(rows, batch_size=batch_size, collate_fn=collate):
        batch = {k: v.to(device) for k, v in batch.items()}
        with torch.autocast('cuda', dtype=torch.float16, enabled=device == 'cuda'):
            output = model(**batch)
        valid = batch['labels'] >= 0
        y, p = batch['labels'][valid], output.logits.argmax(-1)[valid]
        cm += torch.bincount(y * 8 + p, minlength=64).reshape(8, 8).cpu().numpy()
        n = int(valid.sum())
        total_loss += output.loss.item() * n
        positions += n
    metrics = scores(cm)
    metrics['loss'] = total_loss / positions
    return metrics


def profile(args):
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA PyTorch is required for the hardware profile')
    seed_all()
    rows = cache('train')
    # Profile full-length windows, including actual optimizer state allocation.
    candidates = [r for r in rows if len(r['input_ids']) >= 390][:256]
    results = []
    for batch_size in [1, 2, 4]:
        for checkpointing in [False, True]:
            model = optimizer = batch = loss = None
            torch.cuda.empty_cache()
            seed_all()
            try:
                model = init_model().cuda().train()
                if checkpointing:
                    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
                optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=.01)
                scaler = torch.amp.GradScaler('cuda')
                torch.cuda.reset_peak_memory_stats()
                durations, losses = [], []
                for step, rows_batch in enumerate(DataLoader(
                        candidates, batch_size=batch_size, collate_fn=collate, drop_last=True)):
                    if step >= 12:
                        break
                    optimizer.zero_grad(set_to_none=True)
                    batch = {k: v.cuda() for k, v in rows_batch.items()}
                    torch.cuda.synchronize()
                    started = time.perf_counter()
                    with torch.autocast('cuda', dtype=torch.float16):
                        loss = model(**batch).loss
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                    scaler.step(optimizer)
                    scaler.update()
                    torch.cuda.synchronize()
                    durations.append(time.perf_counter() - started)
                    losses.append(loss.item())
                elapsed = float(np.median(durations[3:]))
                result = {'batch_size': batch_size, 'gradient_checkpointing': checkpointing,
                          'status': 'ok', 'median_step_seconds_after_warmup': elapsed,
                          'windows_per_second': batch_size / elapsed,
                          'allocated_peak_mib': torch.cuda.max_memory_allocated() / 2**20,
                          'reserved_peak_mib': torch.cuda.max_memory_reserved() / 2**20,
                          'losses': losses,
                          'estimated_three_epoch_compute_hours': len(rows) * 3 / batch_size * elapsed / 3600}
            except torch.cuda.OutOfMemoryError as exc:
                result = {'batch_size': batch_size, 'gradient_checkpointing': checkpointing,
                          'status': 'cuda_oom', 'message': str(exc)[:500]}
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            del model, optimizer, batch, loss
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            write_json(ROOT / 'results/hardware_profile.json', {
                'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
                'cuda': torch.version.cuda, 'training_windows': len(rows), 'experiments': results,
                'estimate_scope': 'Measured full-length optimizer steps; excludes validation, loading, checkpoint IO.'})


def train(args):
    seed_all()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    rows, validation = cache('train'), cache('validation')
    run = ROOT / 'models' / args.run
    log_dir = ROOT / 'logs' / args.run
    log_dir.mkdir(parents=True, exist_ok=True)
    model = init_model().to(device)
    if args.checkpointing:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=.01)
    steps_per_epoch = math.ceil(math.ceil(len(rows) / args.batch_size) / args.accumulation)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(steps_per_epoch * args.epochs * .1),
                                                steps_per_epoch * args.epochs)
    scaler = torch.amp.GradScaler('cuda', enabled=device == 'cuda')
    tokenizer = AutoTokenizer.from_pretrained(PRETRAINED, local_files_only=True)
    best, history, global_step = -1., [], 0
    config = vars(args) | {'training_windows': len(rows), 'validation_windows': len(validation),
                           'device': device, 'torch': torch.__version__, 'seed': 42,
                           'effective_batch_size': args.batch_size * args.accumulation}
    write_json(ROOT / 'results' / f'{args.run}_config.json', config)
    started = time.perf_counter()
    with (log_dir / 'steps.jsonl').open('w', encoding='utf-8', buffering=1) as log:
        for epoch in range(args.epochs):
            model.train()
            generator = torch.Generator().manual_seed(42 + epoch)
            loader = DataLoader(rows, batch_size=args.batch_size, shuffle=True,
                                generator=generator, collate_fn=collate, num_workers=0)
            optimizer.zero_grad(set_to_none=True)
            running_loss, running_positions = 0., 0
            for step, batch in enumerate(loader):
                batch = {k: v.to(device) for k, v in batch.items()}
                # Last optimizer group may contain fewer micro-batches.
                group_start = step // args.accumulation * args.accumulation
                group_size = min(args.accumulation, len(loader) - group_start)
                with torch.autocast('cuda', dtype=torch.float16, enabled=device == 'cuda'):
                    output = model(**batch)
                    loss = output.loss / group_size
                scaler.scale(loss).backward()
                n = int((batch['labels'] >= 0).sum())
                running_loss += output.loss.item() * n
                running_positions += n
                if (step + 1) % args.accumulation == 0 or step + 1 == len(loader):
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                    old_scale = scaler.get_scale()
                    scaler.step(optimizer)
                    scaler.update()
                    if scaler.get_scale() >= old_scale:
                        scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
                    global_step += 1
                    if global_step % 25 == 0:
                        record = {'epoch': epoch + 1, 'optimizer_step': global_step,
                                  'micro_batch': step + 1, 'micro_batches_in_epoch': len(loader),
                                  'train_loss': running_loss / running_positions,
                                  'lr': scheduler.get_last_lr()[0],
                                  'elapsed_seconds': time.perf_counter() - started}
                        log.write(json.dumps(record) + '\n')
                        print(json.dumps(record), flush=True)
                        running_loss, running_positions = 0., 0
            metrics = evaluate(model, validation, args.eval_batch, device)
            record = {'epoch': epoch + 1, 'optimizer_step': global_step,
                      'elapsed_seconds': time.perf_counter() - started, 'validation': metrics}
            history.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            if metrics['punctuation_micro_f1'] > best:
                best = metrics['punctuation_micro_f1']
                model.save_pretrained(run)
                tokenizer.save_pretrained(run)
                write_json(run / 'training_record.json', record)
            write_json(ROOT / 'results' / f'{args.run}_history.json', history)
    write_json(ROOT / 'results' / f'{args.run}_completion.json', {
        'epochs_completed': args.epochs, 'optimizer_steps': global_step,
        'elapsed_seconds': time.perf_counter() - started, 'best_validation_micro_f1': best,
        'checkpoint': str(run), 'training_articles': 14864})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['cache', 'profile', 'train'])
    parser.add_argument('--batch-size', type=int, default=2)
    parser.add_argument('--accumulation', type=int, default=8)
    parser.add_argument('--eval-batch', type=int, default=4)
    parser.add_argument('--checkpointing', action='store_true')
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--lr', type=float, default=2e-5)
    parser.add_argument('--run', default='news-bert')
    args = parser.parse_args()
    if args.mode == 'cache':
        for split in ['train', 'validation', 'test']:
            cache(split)
    elif args.mode == 'profile':
        profile(args)
    else:
        train(args)
