# P89 二次盲评（一致性检查，test）

> 目的：检查同一评分者在换编号、换顺序后，术语/关系/重大错误是否稳定。
> 本包不含版本名；对应关系在 `key_reliability_test.json`，评完前不要打开。
> 评分写入 `ratings_reliability_test.csv`。
> 只评术语（0–2）、关系（0–2）、重大/次要错误数；不评意象/情感/英语/格式。

## R001 · T10 春晓

**原文**

```text
春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。
```

**术语锚点**

- T10-T1 不觉晓：without realizing it was dawn
- T10-T2 啼鸟：crying birds
- T10-T3 知多少：who knows how many

**关系锚点**

- T10-R1 negation：“不觉晓”是“没察觉到天亮”，不是“天没有亮”。
- T10-R2 auditory-inference：由“闻啼鸟”到“风雨声”再到“花落”，是听觉触发的推断链；诗人没有看见花落。
- T10-R3 question：“花落知多少”是疑问/感叹，不是精确计数。

**译文**

```text
In spring I sleep, unaware of dawn;
Everywhere I hear birds calling.
Last night came the sound of wind and rain—
Who knows how many blossoms fell?
```

---

## R002 · T09 枫桥夜泊

**原文**

```text
月落乌啼霜满天，江枫渔火对愁眠。姑苏城外寒山寺，夜半钟声到客船。
```

**术语锚点**

- T09-T1 姑苏：Suzhou
- T09-T2 寒山寺：Hanshan Temple, near Suzhou
- T09-T3 渔火：fishing-boat lights
- T09-T4 对愁眠：sleep facing sorrow, or sleep accompanied by sorrow; the phrase is ambiguous

**关系锚点**

- T09-R1 juxtaposition：“月落”“乌啼”“霜满天”三个意象并置，不靠显式连接词；不能改写成有因果关系的叙事。
- T09-R2 causal/auditory：“夜半钟声到客船”：钟声从寒山寺传到客船，听觉把远处的寺与近处的船连起来。
- T09-R3 ambiguity：“对愁眠”可解为“面对愁绪而眠”或“愁绪相伴而眠”；两种都保留，不强行改成单一解释。

**译文**

```text
The moon sets, crows cry, frost fills the sky;
River maples and fishing lights face my sorrowful sleep.
Beyond the walls of Gusu stands Cold Mountain Temple;
At midnight its bell reaches the traveler’s boat.
```

---

## R003 · T09 枫桥夜泊

**原文**

```text
月落乌啼霜满天，江枫渔火对愁眠。姑苏城外寒山寺，夜半钟声到客船。
```

**术语锚点**

- T09-T1 姑苏：Suzhou
- T09-T2 寒山寺：Hanshan Temple, near Suzhou
- T09-T3 渔火：fishing-boat lights
- T09-T4 对愁眠：sleep facing sorrow, or sleep accompanied by sorrow; the phrase is ambiguous

**关系锚点**

- T09-R1 juxtaposition：“月落”“乌啼”“霜满天”三个意象并置，不靠显式连接词；不能改写成有因果关系的叙事。
- T09-R2 causal/auditory：“夜半钟声到客船”：钟声从寒山寺传到客船，听觉把远处的寺与近处的船连起来。
- T09-R3 ambiguity：“对愁眠”可解为“面对愁绪而眠”或“愁绪相伴而眠”；两种都保留，不强行改成单一解释。

**译文**

```text
The moon sets, crows caw, frost fills the sky;
River maples and fishing lights face me as I sleep in sorrow.
Beyond the walls of Gusu, Cold Mountain Temple—
At midnight the sound of its bell reaches the traveler’s boat.

Notes:
Gusu: ancient name of Suzhou.
Hanshan Temple: “Cold Mountain Temple,” a Buddhist temple outside Suzhou.
```

---

## R004 · T10 春晓

**原文**

```text
春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。
```

**术语锚点**

- T10-T1 不觉晓：without realizing it was dawn
- T10-T2 啼鸟：crying birds
- T10-T3 知多少：who knows how many

**关系锚点**

- T10-R1 negation：“不觉晓”是“没察觉到天亮”，不是“天没有亮”。
- T10-R2 auditory-inference：由“闻啼鸟”到“风雨声”再到“花落”，是听觉触发的推断链；诗人没有看见花落。
- T10-R3 question：“花落知多少”是疑问/感叹，不是精确计数。

**译文**

```text
Sleeping in spring, I do not know it is dawn;
Everywhere I hear the cries of birds.
Last night came the sound of wind and rain;
Who knows how many flowers have fallen?
```

---
