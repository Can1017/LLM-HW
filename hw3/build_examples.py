"""Draw character-aligned punctuation error figures from actual saved predictions."""
from __future__ import annotations

import json
import math
import unicodedata

from PIL import Image, ImageDraw, ImageFont

from core import read_jsonl
from prepare_data import ROOT, LABELS, write_json

FONT_PATH = 'C:/Windows/Fonts/msyh.ttc'
FONT = ImageFont.truetype(FONT_PATH, 23)
SMALL = ImageFont.truetype(FONT_PATH, 19)
TITLE = ImageFont.truetype(FONT_PATH, 30)
COLORS = {'correct': '#19724B', 'missing': '#C05216', 'extra': '#B32C3E',
          'wrong': '#7343A0', 'ignored': '#708090'}


def special(c):
    return c == '\u3013' or unicodedata.category(c) in {'Co', 'Cf', 'Cc', 'Cs'}


def error_kind(gold, prediction):
    if gold < 0:
        return 'ignored'
    if gold == prediction:
        return 'correct'
    if prediction == 0:
        return 'missing'
    if gold == 0:
        return 'extra'
    return 'wrong'


def draw_example(item, filename, heading, offset=0, limit=102):
    text = item['text'][offset:offset + limit]
    gold = item['labels'][offset:offset + limit]
    pred = item['predictions'][offset:offset + limit]
    assert len(text) == len(gold) == len(pred)
    columns, cell, left, width = 34, 42, 100, 1570
    blocks = math.ceil(len(text) / columns)
    height = 164 + blocks * 112 + 66
    image = Image.new('RGB', (width, height), 'white')
    canvas = ImageDraw.Draw(image)
    canvas.text((28, 18), heading, fill='#152A40', font=TITLE)
    canvas.text((28, 62), f"样例 {item['id']}　正文位置 {offset + 1}—{offset + len(text)}", fill='#4F5C69', font=SMALL)
    legend = [('correct', '标点正确'), ('missing', '× 漏标'), ('extra', '多标'), ('wrong', '类型错误'), ('ignored', '· 不评分')]
    for x, (kind, name) in zip([28, 260, 485, 675, 930], legend):
        canvas.text((x, 101), name, fill=COLORS[kind], font=SMALL)
    for b in range(blocks):
        y = 146 + b * 112
        canvas.line((28, y - 8, width - 28, y - 8), fill='#E4E8EC', width=1)
        canvas.text((28, y + 1), '参考', fill='#46576A', font=SMALL)
        canvas.text((28, y + 46), '预测', fill='#46576A', font=SMALL)
        for j in range(columns):
            i = b * columns + j
            if i >= len(text):
                break
            x = left + j * cell
            kind = error_kind(gold[i], pred[i])
            if kind != 'correct':
                canvas.rectangle((x + 22, y - 1, x + 40, y + 79), fill={
                    'missing': '#FFF0DF', 'extra': '#FBE5E7', 'wrong': '#F0E7F9', 'ignored': '#EEF1F4'}[kind])
            c = text[i]
            display = '□' if special(c) else c
            for row_y in [y, y + 45]:
                if special(c):
                    canvas.rectangle((x - 1, row_y, x + 22, row_y + 28), fill='#FFF2CD')
                canvas.text((x, row_y), display, fill='#263238', font=FONT)
            g = '·' if gold[i] < 0 else LABELS[gold[i]] if gold[i] else ''
            p = LABELS[pred[i]] if pred[i] else '×' if gold[i] > 0 else ''
            canvas.text((x + 22, y), g, fill=COLORS[kind], font=FONT)
            canvas.text((x + 22, y + 45), p, fill=COLORS[kind], font=FONT)
    unusual = sorted({f'U+{ord(c):04X}' for c in text if special(c)})
    note = ('黄色方框 □：原文特殊字符 ' + '、'.join(unusual) + '。') if unusual else '每个正文字符上下对齐；字符右侧为其后标点。图中空白只用于对齐，不进入模型。'
    canvas.text((28, height - 48), note, fill='#576574', font=SMALL)
    path = ROOT / 'figures/examples' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'id': item['id'],
            'offset_start_zero_based': offset, 'displayed_characters': len(text),
            'special_codepoints': unusual,
            'error_counts_in_excerpt': {kind: sum(error_kind(g, p) == kind for g, p in zip(gold, pred))
                                       for kind in ['missing', 'extra', 'wrong', 'ignored']}}


def main():
    manifest = {}
    for corpus, name in [('news', '现代文'), ('cclue', 'CCLUE')]:
        data = {r['id']: r for r in read_jsonl(ROOT / 'data/predictions/news-bert' / f'{corpus}.jsonl')}
        examples = json.loads((ROOT / 'results' / f'news-bert_{corpus}_examples.json').read_text(encoding='utf-8'))
        for e in examples:
            item = data[e['id']]
            title = {'first_medium': '普通样例', 'first_question': '含问号样例',
                     'longest': '最长样例开头', 'lowest_f1_medium': '低分样例'}[e['selection']]
            key = corpus + '_' + e['selection']
            manifest[key] = draw_example(item, key + '.png', f'{name}｜{title}｜标点错误对照')
            if e['selection'] == 'longest' and corpus == 'news':
                manifest['news_seam'] = draw_example(item, 'news_seam.png',
                    '现代文｜窗口接缝 350 附近｜标点错误对照', offset=310, limit=80)
            if corpus == 'cclue' and e['selection'] == 'lowest_f1_medium':
                # Include the full passage containing U+E583 in its original location.
                manifest[key] = draw_example(item, key + '.png', f'{name}｜{title}与源私用字｜标点错误对照', limit=136)
    paragraphs = {r['id']: r for r in read_jsonl(ROOT / 'data/predictions/news-bert/lunyu_paragraphs.jsonl')}
    results = json.loads((ROOT / 'results/news-bert_lunyu.json').read_text(encoding='utf-8'))
    for e in results['examples']:
        key = 'lunyu_' + e['selection']
        manifest[key] = draw_example(paragraphs[e['id']], key + '.png',
                                     f"《论语》｜{ {'opening':'开篇语录', 'longest':'最长语录节选', 'lowest_f1':'人物分类列举'}[e['selection']]}｜标点错误对照")
    write_json(ROOT / 'results/example_figures.json', manifest)
    print(f'Generated {len(manifest)} annotated example figures.')


if __name__ == '__main__':
    main()
