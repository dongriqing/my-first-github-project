# -*- coding: utf-8 -*-
"""
02_analyze.py
把 data/posts.csv 算成 data/stats.json，供 app.py 直接读取。
图表要用到的数字都在这里算完，app.py 只负责画。

数据口径：全部可用的 635 条（自述 + 待核，正文够长），时间跨 2024-08 至 2026-11。
做时间序列时只取近 12 个月（2025-12 至 2026-11，553 条），
更早的那 82 条每个月只有几条，铺不开，只计入总量不做趋势。
"""
import os
import json
import re
from collections import Counter
from datetime import datetime

import pandas as pd
import jieba.posseg as pseg

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

df = pd.read_csv(os.path.join(DATA, "posts.csv"))
df["dt"] = pd.to_datetime(df["publish_time"])
df["ym"] = df["dt"].dt.strftime("%Y-%m")

LABELS = ["直接说情绪", "说身体", "自嘲和反讽", "和别人比", "求助或告别"]

# 近 12 个月，用来画趋势
MONTHS = ["2025-12"] + [f"2026-{m:02d}" for m in range(1, 12)]
MLABEL = {m: m[2:].replace("-", "/") for m in MONTHS}      # 25/12、26/01 …

trend = df[df["ym"].isin(MONTHS)]

# ---------------------------------------------------------------- 基础

n = len(df)
kpi = {
    "notes": n,
    "months": len(MONTHS),
    "trend_notes": int(len(trend)),
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
label_share.sort(key=lambda x: -x["n"])

# 与量表口径的覆盖对比（报告 2.1 的命题一）
covered = sum(x["n"] for x in label_share if x["label"] == "直接说情绪")
kpi["scale_covered_pct"] = round(covered / n * 100, 1)

# ---------------------------------------------------------------- 月度序列

month_series = []
for m in MONTHS:
    sub = trend[trend["ym"] == m]
    month_series.append({
        "month": m,
        "label": MLABEL[m],
        "total": int(len(sub)),
        "by_label": {l: int((sub["label"] == l).sum()) for l in LABELS},
        "sev_mean": round(float(sub["severity"].mean()), 2) if len(sub) else 0,
        "crisis": int(sub["is_crisis"].sum()),
        "heavy_pct": round(float((sub["severity"] == 3).mean() * 100), 1) if len(sub) else 0,
        "len_mean": round(float(sub["char_len"].mean()), 1) if len(sub) else 0,
    })

# 最后两个月 vs 前两个月
delta = []
for l in LABELS:
    last = sum(r["by_label"][l] for r in month_series[-2:])
    prev = sum(r["by_label"][l] for r in month_series[-4:-2])
    pct = round((last - prev) / prev * 100, 1) if prev else 0
    delta.append({"label": l, "last": last, "prev": prev, "pct": pct})

# ---------------------------------------------------------------- 热力图

heat_ml = {"months": [MLABEL[m] for m in MONTHS], "labels": LABELS, "matrix": []}
for l in LABELS:
    heat_ml["matrix"].append([r["by_label"][l] for r in month_series])

days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
df["wd"] = df["dt"].dt.weekday
df["hh"] = df["dt"].dt.hour
m = [[0] * 24 for _ in range(7)]
for _, r in df.iterrows():
    m[int(r["wd"])][int(r["hh"])] += 1
heat_dh = {"days": days, "hours": list(range(24)), "matrix": m}

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
    # 原话：按严重度优先挑，每条裁到 62 字
    q, seen = [], set()
    for _, r in sub.sort_values(["severity", "like_count"], ascending=False).head(80).iterrows():
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
        "heavy_pct": round(sev[2] / len(sub) * 100, 1) if len(sub) else 0,
        "quotes": q[:5],
        "month": [r["by_label"][l] for r in month_series],
        "avg_len": round(float(sub["char_len"].mean()), 1) if len(sub) else 0,
        "crisis": int(sub["is_crisis"].sum()),
    }

# ---------------------------------------------------------------- 危机线

crisis_monthly = [{"month": r["month"], "label": r["label"], "n": r["crisis"]}
                  for r in month_series]
crisis_detail = {
    "total": int(df["is_crisis"].sum()),
    "by_label": {l: int(((df["label"] == l) & (df["is_crisis"] == 1)).sum()) for l in LABELS},
    "peak_month": max(crisis_monthly, key=lambda x: x["n"])["label"],
    "peak_n": max(x["n"] for x in crisis_monthly),
}

stats = {
    "meta": {
        "title": "大学生在小红书上的情绪表达",
        "sub": "从日常抱怨到危机求助 · 635 条笔记观察",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_note": f"{n} 条公开笔记（{df['dt'].min():%Y-%m-%d} 至 {df['dt'].max():%Y-%m-%d}），已脱敏",
        "trend_note": (f"时间序列取近 12 个月（2025-12 至 2026-11，{len(trend)} 条）；"
                       f"更早的 {n - len(trend)} 条每月不足 15 条，只计入总量，不画趋势。"),
        "n": n,
    },
    "kpi": kpi,
    "label_share": label_share,
    "month_series": month_series,
    "delta": delta,
    "heat_ml": heat_ml,
    "heat_dh": heat_dh,
    "topic_detail": topic_detail,
    "crisis": {"monthly": crisis_monthly, **crisis_detail},
}

out = os.path.join(DATA, "stats.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False)

print("已写入", out)
print("总量", n, "趋势段", len(trend))
print(json.dumps(label_share, ensure_ascii=False))
print("重度占比", kpi["sev3_pct"], "% / 危机", kpi["crisis"], "条")
print("月度条数", [(r["label"], r["total"]) for r in month_series])
