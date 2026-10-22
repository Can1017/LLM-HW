import collections
import numpy as np

from prepare_data import clean, LABELS
from core import windows, article_runs, scores, confusion_matrix, Predictor, encode_batch
from prepare_data import ROOT


def test_labels_strip_pronunciation_and_keep_punctuation_after_quotes():
    text, labels = clean('学 而 时 习 之{zhi1} ， 不 亦 说 乎 ？ ”', collections.Counter())
    assert text == '学而时习之不亦说乎'
    assert [LABELS[i] for i in labels] == ['NONE'] * 4 + ['，'] + ['NONE'] * 3 + ['？']


def test_ambiguous_gaps_are_ignored_without_relabelling_them_none():
    text, labels = clean('好 ？！ 甲 —— 乙 。', collections.Counter())
    assert text == '好甲乙'
    assert labels == [-100, -100, 2]


def test_every_input_position_owned_once_including_tail():
    for length in [1, 299, 300, 400, 401, 600, 700, 701, 3501]:
        coverage = np.zeros(length, dtype=int)
        for start, end, a, z in windows(length):
            assert 0 <= start <= a <= z <= end <= length
            coverage[a:z] += 1
        assert (coverage == 1).all()


def test_quarantine_gaps_do_not_join_unrelated_context():
    doc = {'id': 'a', 'paragraphs': [
        {'id': 'a-001', 'text': '甲', 'labels': [0]},
        {'id': 'a-003', 'text': '丙', 'labels': [0]},
        {'id': 'a-004', 'text': '丁', 'labels': [2]}]}
    assert [r['text'] for r in article_runs(doc)] == ['甲', '丙丁']


def test_scores_penalize_wrong_punctuation_type_and_exclude_none():
    cm = confusion_matrix([0, 1, 2, 2, -100], [0, 2, 2, 0, 7])
    metrics = scores(cm)
    assert metrics['punctuation_micro_f1'] == 2 / 5
    assert metrics['scored_positions'] == 4


def test_adaptive_without_period_makes_progress_and_keeps_all_characters():
    predictor = Predictor.__new__(Predictor)
    predictor.predict_windows = lambda texts: [np.zeros(len(t), dtype=np.int16) for t in texts]
    samples = [{'text': '甲' * 1201}, {'text': '乙' * 402}]
    prediction, count = predictor.adaptive(samples, 2)
    assert [len(p) for p in prediction] == [1201, 402]
    assert all((p == 0).all() for p in prediction)
    assert count == 6


def test_actual_tokenizer_preserves_digit_latin_rare_character_label_positions():
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(ROOT / 'models/bert-base-chinese', local_files_only=True)
    texts = ['我爱BERT2026与𠮷字\ue3ab', '甲乙']
    gold = [[0] * (len(texts[0]) - 1) + [2], [1, 2]]
    batch, positions = encode_batch(tokenizer, texts, gold)
    for row, labels in enumerate(gold):
        assert batch['labels'][row, positions[row]].tolist() == labels
        assert len(positions[row]) == len(texts[row])
    assert (batch['labels'][batch['attention_mask'] == 0] == -100).all()
    assert (batch['labels'][:, 0] == -100).all()


def test_error_figure_categories_match_character_labels():
    from build_examples import error_kind, special
    assert error_kind(1, 0) == 'missing'
    assert error_kind(0, 1) == 'extra'
    assert error_kind(1, 2) == 'wrong'
    assert error_kind(2, 2) == 'correct'
    assert error_kind(-100, 2) == 'ignored'
    assert special('〓') and special('\ue583') and not special('字')


def test_published_markdown_uses_absolute_online_targets():
    from public_links import publish_links
    document = publish_links('![图](figures/图.png) [记录](results/a.json) [外部](https://example.org/x)')
    assert 'https://raw.githubusercontent.com/Can1017/LLM-HW/main/hw3/figures/' in document
    assert 'https://github.com/Can1017/LLM-HW/blob/main/hw3/results/a.json' in document
    assert '[外部](https://example.org/x)' in document
