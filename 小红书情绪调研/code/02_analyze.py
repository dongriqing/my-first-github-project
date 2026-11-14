# -*- coding: utf-8 -*-
"""
02_analyze.py
把 posts.csv 算成一份 stats.json，供看板前端直接读取。
所有图表要用的数字都在这里算完，前端只负责画。
"""
import os
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pandas as pd
import jieba
import jieba.posseg as pseg

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

df = pd.read_csv(os.path.join(DATA, "posts.csv"))
df["dt"] = pd.to_datetime(df["publish_time"])

# 统一到"第几周"，起点是第一周的周一
start = datetime(2026, 8, 24)
df["week"] = ((df["dt"] - start).dt.days // 7 + 1).clip(lower=1, upper=12)

LABELS = ["直接说情绪", "说身体", "自嘲和反讽", "和别人比", "求助或告别"]
WEEKS = list(range(1, 13))
week_start = {w: (start + timedelta(days=(w - 1) * 7)).strftime("%m-%d") for w in WEEKS}

# ---------------------------------------------------------------- 基础

n = len(df)
kpi = {
    "notes": n,
    "weeks": 12,
    "avg_len": round(df["char_len"].mean(), 1),
    "median_len": int(df["char_len"].median()),
    "img_share": round(df["has_image"].mean() * 100, 1),
    "crisis": int(df["is_crisis"].sum()),
    "crisis_pct": round(df["is_crisis"].mean() * 100, 2),
    "sev3_pct": round((df["severity"] == 3).mean() * 100, 1),
    "like_median": int(df["like_count"].median()),
    "span": f'{df["dt"].min():%Y-%m-%d} 至 {df["dt"].max():%Y-%m-%d}',
}

label_share = []
for l in LABELS:
    c = int((df["label"] == l).sum())
    label_share.append({"label": l, "n": c, "pct": round(c / n * 100, 1)})

# 与量表口径的覆盖对比（报告 2.1 的命题一）
covered = sum(x["n"] for x in label_share if x["label"] in ("直接说情绪",))
kpi["scale_covered_pct"] = round(covered / n * 100, 1)

# ---------------------------------------------------------------- 周序列

week_series = []
for w in WEEKS:
    sub = df[df["week"] == w]
    row = {"week": w, "start": week_start[w], "total": int(len(sub)),
           "by_label": {l: int((sub["label"] == l).sum()) for l in LABELS},
           "sev_mean": round(float(sub["severity"].mean()), 2) if len(sub) else 0,
           "crisis": int(sub["is_crisis"].sum()),
           "heavy_pct": round(float((sub["severity"] == 3).mean() * 100), 1) if len(sub) else 0,
           "len_mean": round(float(sub["char_len"].mean()), 1) if len(sub) else 0}
    week_series.append(row)

# 最近两周 vs 前两周的环比
def block_mean(a, b, key):
    v = [r[key] for r in week_series if a <= r["week"] <= b]
    return sum(v) / len(v)


delta = []
for l in LABELS:
    last = sum(r["by_label"][l] for r in week_series if r["week"] in (11, 12))
    prev = sum(r["by_label"][l] for r in week_series if r["week"] in (9, 10))
    pct = round((last - prev) / prev * 100, 1) if prev else 0
    delta.append({"label": l, "last": last, "prev": prev, "pct": pct})

# ---------------------------------------------------------------- 热力图

heat_wl = {"weeks": [f"W{w}" for w in WEEKS], "labels": LABELS, "matrix": []}
for l in LABELS:
    heat_wl["matrix"].append([r["by_label"][l] for r in week_series])

days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
df["wd"] = df["dt"].dt.weekday
df["hh"] = df["dt"].dt.hour
hours = list(range(24))
m = [[0] * 24 for _ in range(7)]
for _, r in df.iterrows():
    m[int(r["wd"])][int(r["hh"])] += 1
heat_dh = {"days": days, "hours": hours, "matrix": m}

# ---------------------------------------------------------------- 词频

STOP = set("""
的 了 是 我 也 就 在 有 和 都 不 你 她 他 这 那 一个 什么 还 会 又 到 说 上 去 里
很 但 没 没有 地 得 着 过 自己 我们 你们 他们 现在 时候 感觉 觉得 真的 好像 已经
一直 知道 因为 所以 但是 而且 然后 就是 一点 有点 其实 还是 可以 这样 那样 不是
如果 后来 今天 昨天 明天 别人 事情 东西 一些 这个 那个 一下 起来 出来 下来
有时候 突然 发生 进去 不肯 要死 摆在 过得 很久没 没什么 小时 根本 不该 没事 奇怪 提前 可能 开始 之后 之前 以后 以前 一样 这种 那么 这么 多少
""".split())


KEEP = ("n", "v", "a", "i", "l")   # 名词、动词、形容词、成语、习用语


def words_of(texts):
    c = Counter()
    for t in texts:
        for item in pseg.cut(str(t)):
            w, flag = item.word.strip(), item.flag
            if len(w) < 2 or w in STOP or not flag.startswith(KEEP):
                continue
            if re.fullmatch(r"[\d\W_a-zA-Z]+", w):
                continue
            c[w] += 1
    return c


topic_detail = {}
for l in LABELS:
    sub = df[df["label"] == l]
    c = words_of(sub["text"])
    top = [{"w": w, "n": k} for w, k in c.most_common(26)]
    sev = [int((sub["severity"] == i).sum()) for i in (1, 2, 3)]
    # 原话：按严重度优先挑，每条裁到 60 字
    q, seen = [], set()
    for _, r in sub.sort_values(["severity", "like_count"], ascending=False).head(60).iterrows():
        t = str(r["text"]).replace("\n", " ")
        t = t if len(t) <= 62 else t[:62] + "…"
        key = t[:14]
        if key in seen:
            continue
        seen.add(key)
        q.append({"t": t, "sev": int(r["severity"]), "crisis": int(r["is_crisis"]),
                  "len": int(r["char_len"])})
        if len(q) >= 6:
            break
    topic_detail[l] = {
        "n": int(len(sub)),
        "words": top,
        "sev": sev,
        "quotes": q[:5],
        "week": [r["by_label"][l] for r in week_series],
        "avg_len": round(float(sub["char_len"].mean()), 1),
        "crisis": int(sub["is_crisis"].sum()),
    }

# ---------------------------------------------------------------- 危机线

crisis_weekly = [{"week": w, "start": week_start[w],
                  "n": int(r["crisis"])} for w, r in zip(WEEKS, week_series)]
crisis_detail = {
    "total": int(df["is_crisis"].sum()),
    "by_label": {l: int(((df["label"] == l) & (df["is_crisis"] == 1)).sum()) for l in LABELS},
    "peak_week": max(crisis_weekly, key=lambda x: x["n"])["week"],
    "peak_n": max(x["n"] for x in crisis_weekly),
}

stats = {
    "meta": {
        "title": "大学生在小红书上的情绪表达",
        "sub": "从日常抱怨到危机求助 · 12 周笔记观察",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_note": "示例数据集（演示用，非真实采集）",
        "n": n,
    },
    "kpi": kpi,
    "label_share": label_share,
    "week_series": week_series,
    "delta": delta,
    "heat_wl": heat_wl,
    "heat_dh": heat_dh,
    "topic_detail": topic_detail,
    "crisis": {"weekly": crisis_weekly, **crisis_detail},
}

out = os.path.join(DATA, "stats.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False)

print("已写入", out)
print(json.dumps(label_share, ensure_ascii=False))
print("重度占比", kpi["sev3_pct"], "% / 危机", kpi["crisis"], "条")
print("峰值周 W%d 共 %d 条危机表达" % (crisis_detail["peak_week"], crisis_detail["peak_n"]))
