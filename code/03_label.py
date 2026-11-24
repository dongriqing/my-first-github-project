"""把抓到的原始正文整理成分析用的表，并按标注手册的顺序打一版初标。

输入  data/raw/detail.jsonl   一条一行，抓详情页时落下来的
输出  data/real_posts.csv      字段和 data/posts.csv 一致，可以直接喂给 02_analyze.py

初标是规则打的，只用来跑通流程和看形态，最后要人工抽检一遍再定稿。
"""
import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "detail.jsonl"
OUT = ROOT / "data" / "real_posts.csv"

# ---- 手册第一节：求助或告别（含危机信号）----
CRISIS = re.compile(
    r"不想活|不想再活|活不下去|自杀|结束(自己的)?生命|离开这个世界|"
    r"如果我不在|我要是没了|最后一条|帮我照顾|照顾好我的|交代(完|好)了|"
    r"有人能(跟我|陪我|和我)说说话|我该去哪(看|求助)|撑不住了"
)
HELP = re.compile(
    r"不想活|不想再活|活不下去|最后一条|帮我照顾|照顾好我的|交代(完|好)了|"
    r"有人能(跟我|陪我|和我)说说话|我该去哪(看|求助)|求助|救救我|救救|谁能帮帮我|"
    r"怎么办|该怎么办|该怎么(办|做|调节|走出来)|求建议|求推荐|有没有人(知道|懂|能)|"
    r"谁能(告诉我|说说|帮我)|帮帮我|撑不住了|扛不住了|受不了了"
)

# ---- 手册第二节：自嘲和反讽 ----
IRONY = re.compile(
    r"精神状态(良好|很棒|极佳|非常稳定)|我(很|挺)好(的)?[，,（(]|鼠鼠我啊|吗喽|牛马|"
    r"笑死[，,]?\s*(根本|完全)?笑不出来|笑死[，,]?\s*(其实|可是)|"
    r"积极向上|真是太(棒|好|幸福)了|谢谢[，,]?\s*有被|"
    r"本来(想|说好).{0,12}结果|说好.{0,10}结果|"
    r"我(真|简直)?是个(天才|废物|小丑|笑话)|我配吗|不配(活|拥有|被爱)|"
    r"破防了?|绷不住|嘻嘻.{0,6}不嘻嘻|笑着笑着就哭|"
    r"表面.{0,8}(没事|很好|淡定|坚强)|(假装|装作).{0,8}(没事|很好|开心)"
)

# ---- 手册第三节：身体是叙述主体 ----
BODY = re.compile(
    r"睡不着|失眠|入睡|早醒|吃不下|没胃口|不想吃|掉头发|脱发|心慌|心悸|"
    r"胃疼|胃痛|胃病|头疼|头痛|头晕|眼前发黑|月经|大姨妈|体重|瘦了.{0,3}斤|"
    r"爆痘|喘不上气|呼吸不上来|躯体化|手抖|耳鸣|胸口(疼|闷)"
)
# 只算"顺带提到"的弱身体词，单独出现不归说身体
BODY_WEAK = re.compile(r"累|疲惫|乏力|犯困|眼睛(干|疼|涩)|浑身|没力气|坐不住")
BODY_STRONG = re.compile(r"躯体化|心慌|心悸|手抖|喘不上气|呼吸不上来|眼前发黑|耳鸣")

# ---- 手册第四节：有明确比较对象 ----
COMPARE = re.compile(
    r"室友|舍友|同寝|同宿舍|"
    r"同学(都|已经|拿了|保研|上岸)|"
    r"(别人|人家|他们|她们)(都|已经)|同届|班里.{0,6}都|"
    r"(朋友|闺蜜|发小).{0,8}(保研|上岸|offer|国考|直博|读研)"
)

# ---- 严重程度 ----
SEV3 = re.compile(r"撑不下去|没有意义|想消失|活不下去|不想活|一直没好|越来越糟")
SEV2 = re.compile(
    r"连续.{0,4}(失眠|睡不着|熬夜)|两周|半个月|一个月|旷课|逃课|"
    r"躺了一整天|一天没(吃|起)|作业.{0,4}(没写|交不上)|挂科|暴瘦"
)

TAG_RE = re.compile(r"#[^#\[\]]{1,20}\[话题\]#")


def to_int(v):
    """'1.2万' -> 12000，'' -> 0"""
    if v is None:
        return 0
    s = str(v).strip()
    if not s:
        return 0
    try:
        if s.endswith("万"):
            return int(float(s[:-1]) * 10000)
        if s.endswith("+"):
            return int(float(s[:-1]))
        return int(float(s))
    except ValueError:
        return 0


def label_one(text: str):
    """按手册的五步顺序判，问到哪一步是就停。返回 (label, severity, is_crisis)"""
    crisis = 1 if CRISIS.search(text) else 0

    if HELP.search(text):
        label = "求助或告别"
    elif IRONY.search(text):
        label = "自嘲和反讽"
    elif (len(BODY.findall(text)) >= 2 or BODY_STRONG.search(text)
          or len(BODY_WEAK.findall(text)) >= 2):
        label = "说身体"
    elif COMPARE.search(text):
        label = "和别人比"
    else:
        label = "直接说情绪"

    if crisis or SEV3.search(text):
        sev = 3
    elif SEV2.search(text):
        sev = 2
    else:
        sev = 1
    return label, sev, crisis


def main():
    rows, skipped = [], 0
    for line in RAW.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        raw = (r.get("desc") or r.get("title") or "").strip()
        if len(TAG_RE.sub("", raw)) < 15:      # 太短的多半是纯转发或空壳
            skipped += 1
            continue
        text = TAG_RE.sub("", raw).strip()
        ts = r.get("time")
        try:
            pub = datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            skipped += 1
            continue
        label, sev, crisis = label_one(text)
        rows.append(
            {
                "post_id": r["note_id"],
                "publish_time": pub,
                "text": text,
                "char_len": len(text),
                "tags": "|".join(r.get("tags") or []),
                "has_image": 1 if int(r.get("images") or 0) > 0 else 0,
                "like_count": to_int(r.get("liked")),
                "collect_count": to_int(r.get("collected")),
                "comment_count": to_int(r.get("comment")),
                "label": label,
                "severity": sev,
                "is_crisis": crisis,
            }
        )

    # 按发布时间排，重复的 note_id 只留一条
    rows.sort(key=lambda x: x["publish_time"])
    seen, uniq = set(), []
    for x in rows:
        if x["post_id"] in seen:
            continue
        seen.add(x["post_id"])
        uniq.append(x)

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(uniq[0].keys()))
        w.writeheader()
        w.writerows(uniq)

    print(f"入库 {len(uniq)} 条，剔掉 {skipped} 条（过短或无时间）")
    print(f"时间范围 {uniq[0]['publish_time'][:10]} ~ {uniq[-1]['publish_time'][:10]}")
    print(f"平均字数 {sum(x['char_len'] for x in uniq) / len(uniq):.1f}")
    from collections import Counter

    print("主题分布", dict(Counter(x["label"] for x in uniq)))
    print("严重度", dict(Counter(x["severity"] for x in uniq)))
    print("危机信号", sum(x["is_crisis"] for x in uniq))


if __name__ == "__main__":
    main()
