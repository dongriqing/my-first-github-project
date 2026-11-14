# -*- coding: utf-8 -*-
"""
情绪笔记 · 大学生在小红书上的情绪表达观察
课程个人项目 / Streamlit 应用入口
"""
from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="情绪笔记 · 小红书情绪表达观察",
                   page_icon="🪺", layout="wide")

BASE = Path(__file__).parent
DATA = BASE / "data"

df = pd.read_csv(DATA / "posts.csv")
df["dt"] = pd.to_datetime(df["publish_time"])
S = json.load(open(DATA / "stats.json", encoding="utf-8"))

LABELS = ["直接说情绪", "说身体", "自嘲和反讽", "和别人比", "求助或告别"]
COLORS = {
    "直接说情绪": "#c2543f",
    "说身体": "#bf8f2a",
    "自嘲和反讽": "#6c6ba8",
    "和别人比": "#3a7d8c",
    "求助或告别": "#8c2f39",
}
FONT = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"
INK = "#1c1b19"
MUTED = "#77736d"
GRID = "#ece7db"


def rgba(hexs, a=1.0):
    h = hexs.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def base_layout(fig, height=380, **kw):
    fig.update_layout(
        height=height, font=dict(family=FONT, size=12, color=INK),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(family=FONT, size=12)), **kw)
    if "showlegend" not in kw:
        fig.update_layout(showlegend=False)
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED, size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED, size=11))
    return fig


# ---------------------------------------------------------------- 侧栏
with st.sidebar:
    st.markdown("### 情绪笔记")
    st.caption("大学生在小红书上的情绪表达\n\n12 周 · 1200 条笔记")
    page = st.radio("看哪一块", ["① 总览", "② 主题", "③ 节律"], label_visibility="collapsed")
    st.divider()
    st.caption("**数据说明**")
    st.caption(S["meta"]["data_note"] + "。入库时已替换用户名、学校、地名，"
               "危机信号只在群体层面计数。")
    st.divider()
    st.caption("**如果你正在难受**")
    st.caption("全国心理援助热线 12356\n\n校心理中心 工作日可预约")

k = S["kpi"]

# ---------------------------------------------------------------- ① 总览
if page.startswith("①"):
    st.markdown("## 总览 · 最近十二周整体在什么位置")
    st.caption(f"数据范围 {k['span']}　·　文档生成于 {S['meta']['generated']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("笔记总量", f"{k['notes']:,} 条")
    c2.metric("平均正文长度", f"{k['avg_len']} 字")
    c3.metric("重度表达占比", f"{k['sev3_pct']}%")
    c4.metric("危机信号笔记", f"{k['crisis']} 条")

    ws = pd.DataFrame(S["week_series"])
    left, right = st.columns([1.55, 1])

    with left:
        st.markdown("**每周笔记量 · 按说法拆分**")
        fig = go.Figure()
        for l in LABELS:
            fig.add_trace(go.Scatter(
                x=[f"W{w}" for w in ws["week"]], y=[d[l] for d in ws["by_label"]],
                name=l, mode="lines", stackgroup="one", line=dict(width=0.6, color=COLORS[l]),
                fillcolor=COLORS[l], hovertemplate=f"{l}<br>%{{x}}：%{{y}} 条<extra></extra>"))
        base_layout(fig, height=400, showlegend=True,
                    legend=dict(orientation="h", y=-0.16, font=dict(size=11)))
        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("**五类说法的占比**")
        share = pd.DataFrame(S["label_share"]).sort_values("pct")
        fig = go.Figure(go.Bar(
            x=share["pct"], y=share["label"], orientation="h",
            marker_color=[COLORS[l] for l in share["label"]],
            text=[f"{p}%" for p in share["pct"]], textposition="outside",
            hovertemplate="%{y}：%{x}%<extra></extra>"))
        fig.update_xaxes(range=[0, 36], showgrid=True, gridcolor=GRID)
        base_layout(fig, height=250)
        st.plotly_chart(fig, width="stretch")

        st.markdown("**最近两周 vs 前两周**")
        dl = pd.DataFrame(S["delta"])
        fig = go.Figure(go.Bar(
            x=dl["pct"], y=[l.replace("直接说情绪", "说情绪").replace("自嘲和反讽", "自嘲")
                            .replace("和别人比", "和人比").replace("求助或告别", "求助") for l in dl["label"]],
            orientation="h", marker_color=["#b3372c" if v >= 0 else "#2f7a54" for v in dl["pct"]],
            text=[f"{v:+.1f}%" for v in dl["pct"]], textposition="outside",
            hovertemplate="%{y}：%{x}%<extra></extra>"))
        fig.update_xaxes(range=[-22, 46], showgrid=True, gridcolor=GRID, zeroline=True,
                         zerolinecolor="#d7d0c0")
        base_layout(fig, height=250)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    a, b = st.columns([1.4, 1])
    with a:
        st.markdown("**情绪强度 · 均值与重度占比**")
        sev = [d["sev_mean"] for d in S["week_series"]]
        heavy = [d["heavy_pct"] for d in S["week_series"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[f"W{w}" for w in ws["week"]], y=heavy, name="重度占比(%)",
                             marker_color="#e0cdb4", hovertemplate="%{x} 重度 %{y}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=[f"W{w}" for w in ws["week"]], y=sev, name="平均严重度",
                                 mode="lines+markers", line=dict(color="#8c2f39", width=2.2),
                                 marker=dict(size=6), yaxis="y2",
                                 hovertemplate="%{x} 均值 %{y:.2f}<extra></extra>"))
        base_layout(fig, height=330, showlegend=True,
                    legend=dict(orientation="h", y=1.1, font=dict(size=11)))
        fig.update_layout(yaxis=dict(title="重度占比 %", gridcolor=GRID),
                          yaxis2=dict(title="平均严重度", overlaying="y", side="right",
                                      showgrid=False, range=[1.6, 2.1], dtick=0.1,
                                      tickformat=".1f"))
        st.plotly_chart(fig, width="stretch")
    with b:
        st.markdown("**这段时间里发生了什么**")
        peak = max(S["week_series"], key=lambda d: d["total"])
        low = min(S["week_series"], key=lambda d: d["total"])
        off = 100 - S["label_share"][0]["pct"]
        st.markdown(
            f"- 第 {peak['week']} 周（{peak['start']} 起）最多，{peak['total']} 条；"
            f"第 {low['week']} 周（{low['start']} 起）最少，{low['total']} 条，"
            f"高低差 {peak['total']/low['total']:.1f} 倍。\n"
            f"- 只有“直接说情绪”能和量表对上，占 {S['label_share'][0]['pct']}%；"
            f"其余四类合计 {off:.1f}%，是问卷问不到、平台上却天天在写的那部分。\n"
            f"- 最近两周“和别人比”{dl.loc[3,'pct']:+.1f}%、“求助或告别”{dl.loc[4,'pct']:+.1f}%，"
            f"正好落在秋招和考研报名那几周。")
        st.caption("这几条是读数，不是结论。样本只有十二周，任何一个峰都可能是一周的偶发。")

# ---------------------------------------------------------------- ② 主题
elif page.startswith("②"):
    st.markdown("## 主题 · 五类说法各自长什么样")
    st.caption("选一类，看它的走势、用词和原话。判定顺序写在仓库的标注手册里。")

    cur = st.radio("选一类", LABELS, horizontal=True, label_visibility="collapsed")
    d = S["topic_detail"][cur]
    c = COLORS[cur]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("这一类共", f"{d['n']} 条")
    c2.metric("占全部样本", f"{d['n']/k['notes']*100:.1f}%")
    c3.metric("平均长度", f"{d['avg_len']} 字")
    c4.metric("含危机信号", f"{d['crisis']} 条")

    left, right = st.columns([1, 1])

    with left:
        st.markdown(f"**{cur} · 每周条数**")
        fig = go.Figure(go.Scatter(
            x=[f"W{i+1}" for i in range(12)], y=d["week"], mode="lines+markers",
            line=dict(color=c, width=2.2), marker=dict(size=6),
            fill="tozeroy", fillcolor=rgba(c, 0.12),
            hovertemplate="%{x}：%{y} 条<extra></extra>"))
        base_layout(fig, height=250)
        st.plotly_chart(fig, width="stretch")

        st.markdown("**严重程度分布**")
        fig = go.Figure(go.Bar(
            x=["轻度", "中度", "重度"], y=d["sev"],
            marker_color=["#d9cfb8", "#c08a63", "#8c2f39"],
            text=[f"{v}" for v in d["sev"]], textposition="outside",
            hovertemplate="%{x}：%{y} 条<extra></extra>"))
        base_layout(fig, height=230)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("**这一类的常见用词**")
        w = pd.DataFrame(d["words"][:12]).sort_values("n")
        fig = go.Figure(go.Bar(
            x=w["n"], y=w["w"], orientation="h", marker_color=c,
            text=w["n"], textposition="outside",
            hovertemplate="%{y}：出现 %{x} 次<extra></extra>"))
        fig.update_xaxes(showgrid=True, gridcolor=GRID,
                         range=[0, w["n"].max() * 1.2])
        base_layout(fig, height=330)
        st.plotly_chart(fig, width="stretch")

        tot = sum(d["sev"]) or 1
        sev3 = d["sev"][2] / tot * 100
        st.caption(f"这一类的重度表达占 {sev3:.1f}%，总体是 {k['sev3_pct']}%，"
                   f"{'高' if sev3>k['sev3_pct'] else '低'}出 {abs(sev3-k['sev3_pct']):.1f} 个百分点。")

    st.divider()
    st.markdown("**这一类的几条原话**")
    st.caption("已删去用户名、校名、地名与人名；只作群体观察，不作个体判断。")
    cols = st.columns(2)
    for i, q in enumerate(d["quotes"]):
        with cols[i % 2]:
            tag = "　·　含危机信号" if q["crisis"] else ""
            st.markdown(
                f"> {q['t']}\n>\n> <span style='color:{MUTED};font-size:12px'>"
                f"严重度 {q['sev']}　{q['len']} 字{tag}</span>",
                unsafe_allow_html=True)

# ---------------------------------------------------------------- ③ 节律
else:
    st.markdown("## 节律 · 什么时候最多，哪几周最难受")
    st.caption("把周次和主题交叉起来看，比看总数更能看出是哪一类在涨。")

    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("**学期节律 · 周次 × 主题**")
        hw = S["heat_wl"]
        z = hw["matrix"]
        text = [[str(v) for v in row] for row in z]
        fig = go.Figure(go.Heatmap(
            z=z, x=hw["weeks"], y=hw["labels"], text=text, texttemplate="%{text}",
            textfont=dict(size=11, family=FONT),
            colorscale=[[0, "#f5f1e8"], [1, "#7d2a33"]],
            hovertemplate="%{y} · %{x}：%{z} 条<extra></extra>",
            colorbar=dict(title="条数", thickness=10, len=0.7)))
        base_layout(fig, height=340)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("**危机信号 · 每周条数**")
        cw = pd.DataFrame(S["crisis"]["weekly"])
        fig = go.Figure(go.Bar(
            x=[f"W{w}" for w in cw["week"]], y=cw["n"], marker_color="#8c2f39",
            text=cw["n"], textposition="outside",
            hovertemplate="%{x}：%{y} 条<extra></extra>"))
        base_layout(fig, height=340)
        st.plotly_chart(fig, width="stretch")

        cs = S["crisis"]
        st.caption(f"十二周共 {cs['total']} 条带危机信号，占 {k['crisis_pct']}%，"
                   f"峰值在第 {cs['peak_week']} 周（{cs['peak_n']} 条）。"
                   f"这个数字只说明那一周说这类话的人变多了，不能用来判断任何一个人。")

    st.divider()
    peak = max(S["week_series"], key=lambda d: d["total"])
    low = min(S["week_series"], key=lambda d: d["total"])
    off = 100 - S["label_share"][0]["pct"]
    a, b, c3 = st.columns(3)
    a.markdown("**一 / 总量**")
    a.markdown(f"第 {peak['week']} 周最多（{peak['total']} 条），第 {low['week']} 周最少"
               f"（{low['total']} 条），差 {peak['total']/low['total']:.1f} 倍。不是一条平线。")
    b.markdown("**二 / 结构**")
    b.markdown(f"能和量表对上的只有一类，占 {S['label_share'][0]['pct']}%；"
               f"另外四类合计 {off:.1f}%，问卷问不到。")
    c3.markdown("**三 / 节律**")
    c3.markdown("危机信号不是均匀铺开的，集中在学期中段和秋招那几周。")

st.divider()
st.caption("**伦理边界**　只采公开可见内容 · 入库即脱敏 · 危机信号只做群体计数 · 不做个体预警"
           "　|　如果你正在难受，请拨 12356")
