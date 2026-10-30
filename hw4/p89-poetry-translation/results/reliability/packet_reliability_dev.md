# P89 二次盲评（一致性检查，dev）

> 目的：检查同一评分者在换编号、换顺序后，术语/关系/重大错误是否稳定。
> 本包不含版本名；对应关系在 `key_reliability_dev.json`，评完前不要打开。
> 评分写入 `ratings_reliability_dev.csv`。
> 只评术语（0–2）、关系（0–2）、重大/次要错误数；不评意象/情感/英语/格式。

## R001 · T01 鹿柴

**原文**

```text
空山不见人，但闻人语响。返景入深林，复照青苔上。
```

**术语锚点**

- T01-T2 返景：evening sunlight reflected back into the forest
- T01-T3 青苔：moss

**关系锚点**

- T01-R1 negation：“不见人”是“看不见人”，不是“没有人”；紧接着“但闻人语响”把视觉的否定转为听觉的肯定。
- T01-R2 light/sensory：“返景入深林，复照青苔上”：返照的阳光进入深林，又落在青苔上；光线是移动的，不是静态布景。

**译文**

```text
In the empty mountain no one is seen;
only the sound of voices is heard.
Late sunlight enters the deep forest
and shines again on the green moss.
```

---

## R002 · T02 登鹳雀楼

**原文**

```text
白日依山尽，黄河入海流。欲穷千里目，更上一层楼。
```

**术语锚点**

- T02-T2 千里目：a view stretching a thousand li (li: Chinese mile)
- T02-T3 穷：to exhaust, to reach the end of
- T02-T4 依：to lean against / sink along

**关系锚点**

- T02-R1 purpose-means：“欲穷千里目，更上一层楼”：想看得更远，是目的；“更上一层楼”是手段/条件，不是单纯写景。
- T02-R2 hyperbole：“千里”是夸张的视野，不是精确距离；“一层”也不是字面的一层。
- T02-R3 spatial：白日、山、黄河、海、楼构成由近及远、由下而上的空间推进。

**译文**

```text
The bright sun sinks behind the mountains;
the Yellow River flows into the sea.
To gaze as far as a thousand miles,
climb one more storey.
```

---

## R003 · T01 鹿柴

**原文**

```text
空山不见人，但闻人语响。返景入深林，复照青苔上。
```

**术语锚点**

- T01-T2 返景：evening sunlight reflected back into the forest
- T01-T3 青苔：moss

**关系锚点**

- T01-R1 negation：“不见人”是“看不见人”，不是“没有人”；紧接着“但闻人语响”把视觉的否定转为听觉的肯定。
- T01-R2 light/sensory：“返景入深林，复照青苔上”：返照的阳光进入深林，又落在青苔上；光线是移动的，不是静态布景。

**译文**

```text
In the empty mountain no one is seen;
only the sound of human voices is heard.
Returning sunlight enters the deep forest
and shines again on the green moss.
```

---

## R004 · T01 鹿柴

**原文**

```text
空山不见人，但闻人语响。返景入深林，复照青苔上。
```

**术语锚点**

- T01-T2 返景：evening sunlight reflected back into the forest
- T01-T3 青苔：moss

**关系锚点**

- T01-R1 negation：“不见人”是“看不见人”，不是“没有人”；紧接着“但闻人语响”把视觉的否定转为听觉的肯定。
- T01-R2 light/sensory：“返景入深林，复照青苔上”：返照的阳光进入深林，又落在青苔上；光线是移动的，不是静态布景。

**译文**

```text
No one is seen in the empty mountain,
Only the echo of human voices is heard.
The returning sunlight enters the deep woods,
And shines again on the green moss.
```

---

## R005 · T02 登鹳雀楼

**原文**

```text
白日依山尽，黄河入海流。欲穷千里目，更上一层楼。
```

**术语锚点**

- T02-T2 千里目：a view stretching a thousand li (li: Chinese mile)
- T02-T3 穷：to exhaust, to reach the end of
- T02-T4 依：to lean against / sink along

**关系锚点**

- T02-R1 purpose-means：“欲穷千里目，更上一层楼”：想看得更远，是目的；“更上一层楼”是手段/条件，不是单纯写景。
- T02-R2 hyperbole：“千里”是夸张的视野，不是精确距离；“一层”也不是字面的一层。
- T02-R3 spatial：白日、山、黄河、海、楼构成由近及远、由下而上的空间推进。

**译文**

```text
The white sun sets against the mountains;
The Yellow River flows into the sea.
To exhaust a thousand-li view,
go up one more storey.

Notes
li: a Chinese unit of distance; “a thousand li” is a conventional expression for a vast distance.
```

---

## R006 · T02 登鹳雀楼

**原文**

```text
白日依山尽，黄河入海流。欲穷千里目，更上一层楼。
```

**术语锚点**

- T02-T2 千里目：a view stretching a thousand li (li: Chinese mile)
- T02-T3 穷：to exhaust, to reach the end of
- T02-T4 依：to lean against / sink along

**关系锚点**

- T02-R1 purpose-means：“欲穷千里目，更上一层楼”：想看得更远，是目的；“更上一层楼”是手段/条件，不是单纯写景。
- T02-R2 hyperbole：“千里”是夸张的视野，不是精确距离；“一层”也不是字面的一层。
- T02-R3 spatial：白日、山、黄河、海、楼构成由近及远、由下而上的空间推进。

**译文**

```text
The white sun leans on the mountains and sets;
The Yellow River flows into the sea.
To exhaust a thousand *li* of view,
Climb one more storey of the tower.

Notes
*li*: a Chinese mile.
```

---

## R007 · T02 登鹳雀楼

**原文**

```text
白日依山尽，黄河入海流。欲穷千里目，更上一层楼。
```

**术语锚点**

- T02-T2 千里目：a view stretching a thousand li (li: Chinese mile)
- T02-T3 穷：to exhaust, to reach the end of
- T02-T4 依：to lean against / sink along

**关系锚点**

- T02-R1 purpose-means：“欲穷千里目，更上一层楼”：想看得更远，是目的；“更上一层楼”是手段/条件，不是单纯写景。
- T02-R2 hyperbole：“千里”是夸张的视野，不是精确距离；“一层”也不是字面的一层。
- T02-R3 spatial：白日、山、黄河、海、楼构成由近及远、由下而上的空间推进。

**译文**

```text
The white sun sets behind the mountains,
The Yellow River flows into the sea.
To take in a thousand miles of view,
Climb one more storey of the tower.
```

---

## R008 · T01 鹿柴

**原文**

```text
空山不见人，但闻人语响。返景入深林，复照青苔上。
```

**术语锚点**

- T01-T2 返景：evening sunlight reflected back into the forest
- T01-T3 青苔：moss

**关系锚点**

- T01-R1 negation：“不见人”是“看不见人”，不是“没有人”；紧接着“但闻人语响”把视觉的否定转为听觉的肯定。
- T01-R2 light/sensory：“返景入深林，复照青苔上”：返照的阳光进入深林，又落在青苔上；光线是移动的，不是静态布景。

**译文**

```text
Empty mountain, no one in sight,
only the sound of human voices.
Returning sunlight enters the deep forest,
and shines again on the green moss.
```

---
