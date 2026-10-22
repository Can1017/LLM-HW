"""Restore the seven target punctuation marks in a UTF-8 unpunctuated file."""
from __future__ import annotations

import argparse
from pathlib import Path

import torch

from core import Predictor
from prepare_data import ROOT, LABELS


def punctuate(predictor, text, batch_size):
    # Keep the user's spacing/newlines in the output while the model sees characters.
    characters = ''.join(c for c in text if not c.isspace())
    if not characters:
        return text, 0
    predictions, window_count = predictor.fixed([{'text': characters}], batch_size)
    labels = iter(predictions[0])
    output = []
    for character in text:
        output.append(character)
        if not character.isspace():
            label = int(next(labels))
            if label:
                output.append(LABELS[label])
    return ''.join(output), window_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='UTF-8 text with target punctuation removed')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=8)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error('--batch-size must be positive')
    torch.set_num_threads(4)
    predictor = Predictor(ROOT / 'models/news-bert')
    text = args.input.read_text(encoding='utf-8-sig')
    result, windows = punctuate(predictor, text, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8', newline='') as out:
        out.write(result)
    print(f'Restored {sum(not c.isspace() for c in text):,} characters using {windows} windows. Output: {args.output}')


if __name__ == '__main__':
    main()
