# -*- coding: utf-8 -*-
"""
01_make_dataset.py
生成调研用的小红书风格笔记数据集（示例数据集），并写入 CSV 与 SQLite。

说明：本脚本产出的是演示用样本，用于在没有真实采集结果时跑通全流程。
真实数据到位后，用 01b_import_real.py 导入，字段结构完全一致，
后续 02/03/04 三个脚本不用改一行。
"""
import random
import hashlib
import sqlite3
import csv
import json
import os
from datetime import datetime, timedelta

random.seed(20261114)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

START = datetime(2026, 8, 24)      # 开学前一周，周一
WEEKS = 12
TOTAL = 1200

# ---------------------------------------------------------------- 词库

COURSE = ["高数", "线代", "概率论", "中级财务会计", "成本会计", "审计学", "税法",
          "计量经济学", "Python 课", "统计学", "大学英语", "管理学", "宏观经济学"]
WHO = ["室友", "舍友", "同专业的同学", "高中同学", "隔壁床", "班里的同学",
       "我妈", "学姐", "一起做小组作业的人", "室友"]
PEER = ["室友", "舍友", "同专业的同学", "高中同学", "隔壁床", "班里绩点第一那个",
        "学姐", "一起做小组作业的人"]
SIT = ["图书馆四楼", "自习室", "教学楼六楼"]
PLACE = ["图书馆四楼", "宿舍", "自习室", "教学楼六楼", "食堂二楼", "校医院",
         "操场", "打印店", "通勤的地铁上"]
HOUR = ["凌晨两点", "凌晨三点半", "四点", "早上六点", "中午", "下午三点", "晚上十一点"]
NUM = ["三", "四", "五", "六", "七", "八"]

# ---------------------------------------------------------------- 五类模板

# 1 直接说情绪
T1_OPEN = [
    "最近是真的有点撑不住了。",
    "我不知道该怎么形容这种感觉，就是很难受。",
    "这半个月情绪一直很低，低到自己都觉得陌生。",
    "今天又哭了，第三次了，这个星期。",
    "心里像压了一块东西，说不上来是什么。",
    "已经连续好多天，醒来第一件事是觉得烦。",
    "我一直以为自己挺能扛的，最近发现不行。",
    "有点想不通，为什么我这么容易就崩。",
    "今天在{place}坐着，突然就想哭，也没发生什么。",
    "情绪这个东西真的很奇怪，明明什么都没变，就是提不起劲。",
]
T1_MID = [
    "没发生什么大事，就是一件一件小事堆在一起，堆到最后连{hour}醒来都觉得累。",
    "白天上课还能装正常，一回到宿舍就整个人塌下来。",
    "不想跟任何人说话，{who}问我怎么了我也说不出来。",
    "在{sit}坐下，翻开那本{course}，突然就不想动了。",
    "我知道该做什么，我知道要起来，但我就是起不来。",
    "刷手机刷到{hour}，明明困得要死，还是不肯睡，也不知道在等什么。",
    "想过要不要去校医院看看，又觉得好像没严重到那个程度。",
    "跟{peer}讲了，对方说想开点，我就没再讲了。",
    "有时候会突然很想哭，有时候又一整天什么感觉都没有。",
    "我甚至说不清是难过还是空，就是没有力气。",
]
T1_END = [
    "写下来好像好一点，虽然也没什么用。",
    "不知道有没有人跟我一样。",
    "明天还要上{course}，先睡吧。",
    "就这样吧，明天再说。",
    "说出来好像轻松一点点。",
    "希望过几天能好。",
    "算了，写完删。",
]

# 2 说身体
T2_OPEN = [
    "身体比嘴诚实。",
    "最近身体在报警，我还在硬撑。",
    "连续{NUM}天凌晨{hour2}睡了，今天照镜子吓一跳。",
    "胃又开始疼了，一紧张就疼，老毛病。",
    "掉头发掉到我自己都害怕。",
    "这两个月瘦了{NUM}斤，不是减肥。",
    "心跳很快，坐着也很快，去校医院查了说没事。",
    "最近老是吃不下，一份饭扒两口就饱了。",
    "头疼，{hour}疼醒的那种。",
    "脸上爆了一片，作息乱成这样也是活该。",
]
T2_MID = [
    "早上起不来，起来了也像没睡，一整天脑子是糊的。",
    "{course}的课上坐着，眼睛睁着，什么都没听进去。",
    "已经很久没有好好吃过一顿饭了，都是{place}随便买点。",
    "想去操场跑两圈，走到门口又回来了。",
    "手会抖，尤其是要交作业那两天。",
    "月经也乱了，两个月没来，我有点怕。",
    "胸口闷，深呼吸也闷，{who}说我脸色很差。",
    "有时候站起来会眼前一黑，站一会儿才缓过来。",
    "去校医院，医生说注意休息，可我没有时间休息。",
    "药吃了，好像也没什么用。",
]
T2_END = [
    "知道这样下去不行，但不知道从哪改。",
    "有没有人教我怎么把作息调回来。",
    "明天开始早睡，第{NUM}次立这个 flag。",
    "身体是自己的，道理都懂。",
    "先记一下，看看还能撑多久。",
    "周末一定要睡一天。",
]

# 3 自嘲和反讽
T3_OPEN = [
    "精神状态良好。",
    "我很好，真的，非常好。",
    "鼠鼠我啊，是真的要完蛋了。",
    "当代大学生的精神状态，如图所示。",
    "本人目前情绪稳定（稳定地崩）。",
    "积极向上的一天（从床上爬起来用了四十分钟）。",
    "最近在自我提升（指{hour}还在刷手机）。",
    "感谢{course}，让我知道什么叫人间清醒。",
    "大三，身体健康，心态平和，一切尽在掌握（以上均为虚构）。",
    "今日份的快乐（图一是我的{course}成绩）。",
]
T3_MID = [
    "早上给自己定了六个闹钟，最后是被{peer}叫醒的。",
    "计划表写了一整页，完成了一项：写计划表。",
    "说好今天晚上写作业，现在快十二点了，我在整理桌面图标。",
    "看了三小时书，翻了两页。",
    "图书馆占座成功，坐下之后开始想人生。",
    "把 ddl 提前一周，然后提前一周开始焦虑。",
    "手机屏幕使用时间 11 小时，其中 4 小时在{place}发呆。",
    "跟{peer}说我在忙，其实在躺着看天花板。",
    "买了{NUM}本教辅，一本没拆封。",
    "这个月生活费又超了，主要花在奶茶和外卖上。",
]
T3_END = [
    "哈哈，没事，我很好。",
    "笑死，根本笑不出来。",
    "不说了，去学习了（去床上）。",
    "以上，一个废物的一天。",
    "谢谢大家，我这就去努力（躺下）。",
    "救命。",
]

# 4 和别人比
T4_OPEN = [
    "{who}保研了。",
    "刷到{peer}发的实习 offer，{place}坐了很久。",
    "同一个班，同一门{course}，人家 95，我 61。",
    "别人的大三：实习、比赛、雅思。我的大三：补考。",
    "{who}今天发了朋友圈，配图是某大厂的工牌。",
    "看到年级群里的排名，我把手机反过来放了十分钟。",
    "妈妈打电话问我在学校怎么样，我说挺好的。",
    "高中坐我后面的那个，现在在某 985 直博。",
    "我们宿舍六个人，五个有方向，只有我在原地。",
    "刚刚知道{who}拿了国奖。",
]
T4_MID = [
    "我不是不努力，我每天也在{place}坐到闭馆，但就是差一截。",
    "她早上六点起，我六点还在睡，这能怪谁。",
    "我知道不该比较，可这些信息就摆在那里，一刷就是。",
    "简历改到第{NUM}版，还是空的。",
    "面试被问“你最大的优势是什么”，我卡了半分钟。",
    "家里人觉得我读了大学就该有出息，我不敢说我连实习都没找到。",
    "看着他们讨论保研、出国、考公，我插不上话。",
    "有一瞬间希望她过得没那么好，然后我为自己这个念头难受了很久。",
    "同样的四年，怎么就差这么多。",
    "不是嫉妒，是慌。",
]
T4_END = [
    "算了，各人有各人的路。",
    "说出来好受一点。",
    "明天继续改简历。",
    "有没有跟我一样的，评论区集合。",
    "不看了，卸载两天。",
    "希望明年这个时候我也能发一条。",
]

# 5 求助或告别
T5_OPEN = [
    "有人能跟我说说话吗。",
    "不知道该跟谁说，就发在这里了。",
    "如果这条有人看到，能不能回我一句。",
    "我可能需要一点帮助，但我不知道去哪找。",
    "很久没有跟人好好说过话了。",
    "今天第一次认真想了“如果我不在了会怎么样”。",
    "写这条的时候手在抖。",
    "我不知道这是不是在求救，但我确实快撑不住了。",
    "如果我不在了，帮我照顾一下我的猫。",
    "这可能是最后一条。",
]
T5_MID = [
    "我不想让家里知道，他们会更担心。",
    "学校有心理咨询，我走到门口又回来了，怕被记档案。",
    "{peer}说我最近很奇怪，我说没事。",
    "每天醒来第一个念头是“又要过一天”。",
    "我已经很久没有觉得哪件事有意思了。",
    "该交代的好像都交代完了，反而轻松了一点。",
    "对不起，我知道这样说很自私。",
    "我只是想有人知道我今天很难。",
    "打了很多字又删了，这条也可能会删。",
    "医生说要按时吃药，我停了，因为吃了很困，我还要上课。",
]
T5_END = [
    "谢谢看到这里的人。",
    "如果有人知道怎么办，请告诉我。",
    "我明天会去心理中心看看。",
    "就这样吧。",
    "晚安。",
    "对不起。",
]

TEMPLATES = {
    "直接说情绪": (T1_OPEN, T1_MID, T1_END),
    "说身体": (T2_OPEN, T2_MID, T2_END),
    "自嘲和反讽": (T3_OPEN, T3_MID, T3_END),
    "和别人比": (T4_OPEN, T4_MID, T4_END),
    "求助或告别": (T5_OPEN, T5_MID, T5_END),
}


EXTRA = {
    "直接说情绪": [
        "上周的{course}作业也是拖到最后一天才交的。",
        "这两天连{place}都不太想去了，去了也坐不住。",
        "手机里存了一堆没看的资料，一个都没打开。",
        "想找个理由哭一场，又觉得没什么好哭的。",
        "朋友圈刷到大家的日常，我连点赞的力气都没有。",
        "有时候觉得自己挺矫情的，过两天又觉得是真的难受。",
        "不想让{who}看出来，就装作在忙。",
        "晚上躺着会想很多，想到最后也不知道在想什么。",
    ],
    "说身体": [
        "上周体测跑八百米，跑完蹲在地上十分钟没起来。",
        "最近一吃东西就反胃，只能喝点粥。",
        "眼睛干得厉害，滴眼药水也没什么用。",
        "脖子和肩膀一直是僵的，低头看一会儿书就疼。",
        "白天犯困，晚上精神，完全反过来了。",
        "去校医院量了血压，医生说偏低，让我多吃点。",
        "咖啡从一天一杯变成三杯，还是不顶用。",
        "上次体检报告还在抽屉里没敢看。",
    ],
    "自嘲和反讽": [
        "书桌收拾得干干净净，因为根本没在学。",
        "作业截止前两小时开始，效率高得吓人。",
        "跟{peer}约了去{place}，两个人坐了一下午，各自刷手机。",
        "体重涨了{NUM}斤，说是压力肥，其实就是吃得多。",
        "买了健身卡，去了两次，一次是办卡那天。",
        "专业课听懂了，就是不会做题。",
        "已经想好寒假怎么逆袭了，去年也是这么想的。",
        "刚在朋友圈发完“加油”，转头打开短视频。",
    ],
    "和别人比": [
        "她的简历我看了，密密麻麻，我一页写不满。",
        "一起上课的{peer}已经在准备雅思了，我连四级都还没过。",
        "家里的群里在转“某某学长保研清北”，我妈还@了我。",
        "不是没想过努力，是不知道往哪使劲。",
        "辅导员说大三要定方向，我到现在还没定。",
        "打开招聘软件，看了一圈，没有一条是我能投的。",
        "同龄人已经开始收网了，我还在找网。",
        "有时候会想，如果我当初选了别的专业会不会好一点。",
    ],
    "求助或告别": [
        "我给心理热线打过一次，响了很久没人接，我就挂了。",
        "室友在打游戏，我戴着耳机坐了一晚上。",
        "其实我很想有人问我一句“你还好吗”，认真的那种问。",
        "昨天把房间收拾了一遍，东西都归了位。",
        "不知道该不该跟辅导员说，怕被叫家长。",
        "我知道这些想法不对，但我控制不住。",
        "白天还能笑，晚上就不行了。",
        "写了很长一段，全删了，只剩这几句。",
    ],
}

TAGS = {
    "直接说情绪": ["#情绪", "#树洞", "#大学生日常", "#emo了", "#心情"],
    "说身体": ["#失眠", "#作息", "#身体健康", "#焦虑躯体化", "#熬夜"],
    "自嘲和反讽": ["#精神状态", "#大学生", "#自嘲", "#摆烂", "#日常"],
    "和别人比": ["#保研", "#实习", "#同辈压力", "#大三", "#焦虑"],
    "求助或告别": ["#求助", "#树洞", "#撑不住了", "#心理", "#需要帮助"],
}

# 每周权重：第 2 周开学、第 5 周体测与小测、第 8 周期中、第 11 周秋招与考研报名
WEEK_W = [0.72, 1.18, 1.00, 1.06, 1.22, 0.94, 0.99, 1.34, 1.02, 0.98, 1.28, 0.88]

# 五类基础占比
LABEL_P = {"直接说情绪": 0.30, "说身体": 0.21, "自嘲和反讽": 0.25,
           "和别人比": 0.15, "求助或告别": 0.09}

# 峰值周的主题加成
WEEK_BOOST = {
    1: {"直接说情绪": 1.25, "说身体": 1.10},
    4: {"说身体": 1.45, "自嘲和反讽": 1.15},
    7: {"直接说情绪": 1.35, "求助或告别": 1.30},
    8: {"直接说情绪": 1.20},
    10: {"和别人比": 1.55, "求助或告别": 1.25},
}


def fill(t):
    return t.format(
        course=random.choice(COURSE), who=random.choice(WHO),
        place=random.choice(PLACE), hour=random.choice(HOUR),
        hour2=random.choice(["一", "两", "三"]),
        sit=random.choice(SIT), peer=random.choice(PEER),
        NUM=random.choice(NUM),
    )


def pick(pool, used):
    """同一篇里不重复用句子"""
    for _ in range(14):
        s = fill(random.choice(pool))
        if s not in used:
            return s
    return fill(random.choice(pool))


def make_text(label):
    op, mid, end = TEMPLATES[label]
    used = set()
    parts = []
    for pool, n in ((op, 1), (mid, random.randint(2, 3)),
                    (EXTRA[label], random.randint(1, 2))):
        for _ in range(n):
            s = pick(pool, used)
            used.add(s)
            parts.append(s)
    parts.append(pick(end, used))
    # 小红书式换行：句群之间偶尔空一行
    txt = ""
    for i, p in enumerate(parts):
        txt += p
        if i < len(parts) - 1:
            txt += "\n" if random.random() < 0.35 else ""
    return txt.strip()


def pick_label(boost):
    keys = list(LABEL_P)
    w = [LABEL_P[k] * boost.get(k, 1.0) for k in keys]
    return random.choices(keys, weights=w, k=1)[0]


rows = []
week_posts = []
for w in range(WEEKS):
    base = TOTAL * WEEK_W[w] / sum(WEEK_W)
    week_posts.append(int(round(base)))

diff = TOTAL - sum(week_posts)
week_posts[7] += diff

pid = 0
for w, n in enumerate(week_posts):
    boost = WEEK_BOOST.get(w, {})
    for _ in range(n):
        pid += 1
        label = pick_label(boost)
        text = make_text(label)

        # 发布时刻：多集中在夜里
        day = START + timedelta(days=w * 7 + random.randint(0, 6))
        if day > datetime(2026, 11, 14):
            day = datetime(2026, 11, 14)
        hh = random.choices([8, 10, 13, 15, 18, 21, 22, 23, 0, 1, 2, 3],
                            weights=[3, 4, 5, 5, 7, 14, 18, 16, 12, 10, 8, 4])[0]
        mm = random.randint(0, 59)
        dt = day.replace(hour=hh, minute=mm)

        # 严重程度
        r = random.random()
        if label == "求助或告别":
            sev = 3 if r < 0.55 else (2 if r < 0.9 else 1)
        elif label == "自嘲和反讽":
            sev = 1 if r < 0.45 else (2 if r < 0.9 else 3)
        elif label == "和别人比":
            sev = 1 if r < 0.35 else (2 if r < 0.85 else 3)
        else:
            sev = 1 if r < 0.4 else (2 if r < 0.88 else 3)

        # 危机信号：求助类为主，其余类别低频命中
        if label == "求助或告别":
            crisis = 1 if random.random() < 0.34 else 0
        else:
            crisis = 1 if random.random() < 0.008 else 0

        like = int(min(30000, max(0, random.lognormvariate(3.2, 1.35))))
        if sev == 3 and random.random() < 0.5:
            like = int(like * 1.8)

        rows.append({
            "post_id": hashlib.md5(f"note-{pid}".encode()).hexdigest()[:12],
            "publish_time": dt.strftime("%Y-%m-%d %H:%M"),
            "week": w + 1,
            "text": text,
            "char_len": len(text.replace("\n", "")),
            "tags": " ".join(random.sample(TAGS[label], k=min(3, len(TAGS[label])))),
            "has_image": 1 if random.random() < 0.47 else 0,
            "like_count": like,
            "collect_count": int(like * random.uniform(0.15, 0.9)),
            "comment_count": int(like * random.uniform(0.03, 0.25)),
            "label": label,
            "severity": sev,
            "is_crisis": crisis,
            "label_source": "sample",
        })

rows.sort(key=lambda r: r["publish_time"])
for r in rows:
    r.pop("week")

# ---------------------------------------------------------------- 落盘

csv_path = os.path.join(DATA, "posts.csv")
fields = list(rows[0].keys())
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

db_path = os.path.join(DATA, "posts.db")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
con.execute("""
CREATE TABLE posts (
    post_id      TEXT PRIMARY KEY,
    publish_time TEXT,
    text         TEXT,
    char_len     INTEGER,
    tags         TEXT,
    has_image    INTEGER,
    like_count   INTEGER,
    collect_count INTEGER,
    comment_count INTEGER,
    label        TEXT,
    severity     INTEGER,
    is_crisis    INTEGER,
    label_source TEXT
)
""")
con.executemany(
    "INSERT INTO posts VALUES (:post_id,:publish_time,:text,:char_len,:tags,"
    ":has_image,:like_count,:collect_count,:comment_count,:label,:severity,"
    ":is_crisis,:label_source)", rows)
con.commit()
con.close()

print(f"写入 {len(rows)} 条 -> {csv_path}")
print("时间范围", rows[0]["publish_time"], "至", rows[-1]["publish_time"])
print("平均字数", round(sum(r["char_len"] for r in rows) / len(rows), 1))

print("\n---- 抽样 8 条 ----")
for r in random.sample(rows, 8):
    print(f"\n[{r['publish_time']}] {r['label']} / 严重度{r['severity']} / 危机{r['is_crisis']}")
    print(r["text"])
