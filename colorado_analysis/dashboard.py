"""
CU Boulder MSDS — InScribe Community Analysis Dashboard
"""
import html, re, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
from pathlib import Path
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="CU Boulder MSDS — InScribe Analysis",
    page_icon="🎓", layout="wide",
)
st.markdown("""
<style>
[data-testid="metric-container"]{background:#f0f4ff;border-radius:10px;padding:10px 14px;}
.block-container{padding-top:1.2rem;}
h2{margin-top:0.2rem;}
</style>""", unsafe_allow_html=True)

OUT = Path(__file__).parent

CHANNEL_COLORS = {
    "General": "#4361EE",
    "Machine Learning": "#F72585",
    "Statistical Modeling for Data Science": "#7209B7",
    "Data Mining Foundations and Practice": "#3A0CA3",
    "Data Science Foundations: Statistical Inference": "#4CC9F0",
    "Data Science Methods for Quality Improvement": "#06D6A0",
    "Vital Skills": "#FFB703",
    "Databases": "#FB8500",
    "Text Market Analytics": "#E63946",
    "Bayesian Statistics": "#2DC653",
    "Modeling and Predicting Climate Anomalies": "#00B4D8",
    "Data Science Foundations: Data Structures and Algorithms": "#9D4EDD",
    "High Performance and Parallel Computing": "#FF6B6B",
    "Computer Vision": "#48CAE4",
    "Industry Collaboration: IBM Capstone Project": "#F4A261",
    "Statistical Learning for Data Science": "#E9C46A",
    "Deep Learning Applications for Computer Vision": "#264653",
    "Effective Communication": "#A8DADC",
    "NLP: Natural Language Processing": "#457B9D",
    "Security and Ethical Hacking": "#1D3557",
    "Internet Policy": "#E07A5F",
    "High Performance and Parallel Computing": "#3D405B",
}

def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(t or "")))).strip()

@st.cache_data
def load():
    df = pd.read_csv(OUT / "conversations.csv")
    for col in ["title", "body", "author", "channel", "last_responder"]:
        df[col] = df[col].apply(clean)
    for col in ["view_count", "response_count", "reply_count", "reaction_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce", utc=True)
    df["last_response"] = pd.to_datetime(df["last_response"], errors="coerce", utc=True)
    df.loc[df["last_response"].dt.year < 2000, "last_response"] = pd.NaT
    df["response_hours"] = (df["last_response"] - df["created_date"]).dt.total_seconds() / 3600
    df["month"] = df["created_date"].dt.to_period("M").astype(str)
    df["week"]  = df["created_date"].dt.to_period("W").astype(str)
    df["type_label"] = df["type"].map({
        "helpQuestion": "Help / Question",
        "sharePost":    "Share / Resource",
        "liveSession":  "Live Session",
    }).fillna(df["type"])
    df["short_title"] = df["title"].apply(lambda t: t[:60] + "…" if len(t) > 60 else t)
    df["engagement"]  = df["view_count"] + df["response_count"] * 15 + df["reaction_count"] * 8
    df["has_responses"] = df["response_count"] > 0
    df["is_anonymous"]  = df["is_anonymous"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df

df = load()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🔎 Filters")
channels = ["All Channels"] + sorted(df["channel"].dropna().unique().tolist())
sel_ch   = st.sidebar.selectbox("Channel", channels)
types    = ["All Types"] + sorted(df["type_label"].dropna().unique().tolist())
sel_type = st.sidebar.selectbox("Post Type", types)
months   = sorted(df["month"].dropna().unique().tolist())
sel_months = st.sidebar.multiselect("Month(s)", months, default=months)

fdf = df.copy()
if sel_ch   != "All Channels": fdf = fdf[fdf["channel"] == sel_ch]
if sel_type != "All Types":    fdf = fdf[fdf["type_label"] == sel_type]
if sel_months: fdf = fdf[fdf["month"].isin(sel_months)]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🎓 CU Boulder MSDS — InScribe Community Analysis")
st.caption("Scraped from the CU Boulder Data Science Community on InScribe · Dec 2025 – Jun 2026 · Built with Python + Streamlit")
st.markdown("---")

# ── KPIs ─────────────────────────────────────────────────────────────────────
k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
k1.metric("Total Posts",      f"{len(fdf):,}")
k2.metric("Total Views",      f"{fdf['view_count'].sum():,}")
k3.metric("Avg Views/Post",   f"{fdf['view_count'].mean():.0f}")
k4.metric("Channels w/ Posts", f"{fdf['channel'].nunique()} / 22")
k5.metric("Unique Authors",   fdf["author"].nunique())
k6.metric("Questions Asked",  int((fdf["type_label"] == "Help / Question").sum()))
k7.metric("Answered",         f"{int(fdf['has_answer'].astype(str).str.lower().isin(['true','1']).sum())}/{len(fdf)}")

st.markdown("---")

# ══ TAB LAYOUT ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", "🔥 Content", "⏱️ Activity & Time", "👤 Authors", "💬 Q&A Deep Dive"
])

# ═══════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════
with tab1:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("Posts per Channel")
        ch_df = fdf.groupby("channel").agg(
            Posts=("id", "count"),
            Views=("view_count", "sum"),
            Avg_Views=("view_count", "mean"),
        ).sort_values("Posts", ascending=True).reset_index()
        fig = px.bar(ch_df, x="Posts", y="channel", orientation="h",
                     color="channel", color_discrete_map=CHANNEL_COLORS,
                     text="Posts",
                     labels={"channel": "", "Posts": "# Posts"})
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=480, margin=dict(l=0,r=40,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Post Type Breakdown")
        type_df = fdf.groupby("type_label").agg(
            Count=("id", "count"),
            Views=("view_count", "sum"),
        ).reset_index()
        fig2 = px.pie(type_df, names="type_label", values="Count",
                      color_discrete_sequence=["#4361EE","#F72585","#FFB703"],
                      hole=0.4)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(showlegend=False, height=260, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Views by Channel (Top 8)")
        top_ch = fdf.groupby("channel")["view_count"].sum().nlargest(8).reset_index()
        fig3 = px.bar(top_ch, x="channel", y="view_count",
                      color="channel", color_discrete_map=CHANNEL_COLORS,
                      labels={"channel": "", "view_count": "Total Views"})
        fig3.update_layout(showlegend=False, height=210,
                           margin=dict(l=0,r=0,t=10,b=60),
                           xaxis_tickangle=-35)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # Channel stats table
    st.subheader("Channel Summary Table")
    ch_summary = fdf.groupby("channel").agg(
        Posts=("id","count"),
        Total_Views=("view_count","sum"),
        Avg_Views=("view_count","mean"),
        Total_Reactions=("reaction_count","sum"),
        Questions=("type_label", lambda x: (x=="Help / Question").sum()),
        Shares=("type_label", lambda x: (x=="Share / Resource").sum()),
        Unanswered=("has_responses", lambda x: (~x).sum()),
        Unique_Authors=("author", "nunique"),
    ).sort_values("Posts", ascending=False).reset_index()
    ch_summary["Avg_Views"] = ch_summary["Avg_Views"].round(0).astype(int)
    st.dataframe(ch_summary.rename(columns={
        "channel":"Channel","Total_Views":"Total Views","Avg_Views":"Avg Views/Post",
        "Total_Reactions":"Reactions","Unique_Authors":"Unique Authors"
    }), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════
# TAB 2 — CONTENT (MOST VIEWED / ENGAGED)
# ═══════════════════════════════════════════════════════════
with tab2:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("🔥 Top 15 Most Viewed Posts")
        top = fdf.nlargest(15, "view_count").sort_values("view_count")
        fig = px.bar(top, x="view_count", y="short_title", orientation="h",
                     color="channel", color_discrete_map=CHANNEL_COLORS,
                     text="view_count",
                     labels={"view_count":"Views","short_title":""})
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(height=520, margin=dict(l=0,r=50,t=10,b=10),
                          legend_title="Channel")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("💥 Top 10 by Engagement Score")
        st.caption("Score = views + responses×15 + reactions×8")
        top_eng = fdf.nlargest(10, "engagement")[["short_title","channel","engagement","view_count","response_count","reaction_count"]]
        st.dataframe(top_eng.rename(columns={
            "short_title":"Title","channel":"Channel",
            "engagement":"Score","view_count":"Views",
            "response_count":"Responses","reaction_count":"Reactions"
        }), use_container_width=True, hide_index=True, height=280)

        st.subheader("⭐ Most Reacted Posts")
        top_react = fdf.nlargest(8, "reaction_count")[["short_title","channel","reaction_count","view_count"]]
        fig_r = px.bar(top_react.sort_values("reaction_count"),
                       x="reaction_count", y="short_title", orientation="h",
                       color="channel", color_discrete_map=CHANNEL_COLORS,
                       text="reaction_count",
                       labels={"reaction_count":"Reactions","short_title":""})
        fig_r.update_layout(showlegend=False, height=260, margin=dict(l=0,r=30,t=10,b=10))
        st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("💬 Views vs Responses (Bubble = Reactions)")
        fig_sc = px.scatter(
            fdf, x="response_count", y="view_count",
            size="reaction_count", size_max=35,
            color="channel", color_discrete_map=CHANNEL_COLORS,
            hover_name="title",
            hover_data={"response_count":True,"reaction_count":True,"channel":False},
            labels={"response_count":"Responses","view_count":"Views"},
        )
        fig_sc.update_layout(height=380, legend_title="Channel", margin=dict(l=0,r=0,t=10,b=10))
        st.plotly_chart(fig_sc, use_container_width=True)

    with c4:
        st.subheader("☁️ Word Cloud — Topics & Keywords")
        text = " ".join(fdf["title"].fillna("") + " " + fdf["body"].fillna(""))
        stopwords = {
            "the","a","an","and","or","in","of","to","is","it","for","i","this",
            "that","my","me","we","be","with","are","on","have","has","was","but",
            "from","as","so","if","by","at","not","they","their","them","its","our",
            "you","your","http","https","www","com","just","can","do","all","any",
            "also","would","could","should","will","been","than","then","when","where",
            "how","what","which","who","there","here","one","two","get","got","use",
            "using","used","am","im","course","class","hi","hey","help","need","want",
        }
        if text.strip():
            wc = WordCloud(width=700, height=380, background_color="white",
                           colormap="cool", max_words=100,
                           stopwords=stopwords, collocations=True).generate(text)
            fig_wc, ax = plt.subplots(figsize=(7, 3.8))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            plt.tight_layout(pad=0)
            st.pyplot(fig_wc)

# ═══════════════════════════════════════════════════════════
# TAB 3 — ACTIVITY & TIME
# ═══════════════════════════════════════════════════════════
with tab3:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📅 Monthly Posting Activity")
        monthly = fdf.groupby(["month","type_label"]).size().reset_index(name="Posts")
        fig_m = px.bar(monthly, x="month", y="Posts", color="type_label",
                       color_discrete_sequence=["#4361EE","#F72585","#FFB703"],
                       barmode="stack",
                       labels={"month":"Month","Posts":"# Posts","type_label":"Type"})
        fig_m.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=10),
                             xaxis_tickangle=-30, legend_title="Post Type")
        st.plotly_chart(fig_m, use_container_width=True)

    with c2:
        st.subheader("⏱️ Response Time Distribution")
        rt = fdf["response_hours"].dropna()
        rt = rt[rt > 0]
        if len(rt) > 1:
            fig_rt = px.histogram(rt, nbins=15,
                                  color_discrete_sequence=["#4361EE"],
                                  labels={"value":"Hours to First Response","count":"Posts"})
            fig_rt.add_vline(x=rt.mean(), line_dash="dash", line_color="red",
                             annotation_text=f"Mean {rt.mean():.0f}h")
            fig_rt.add_vline(x=rt.median(), line_dash="dot", line_color="orange",
                             annotation_text=f"Median {rt.median():.0f}h")
            fig_rt.update_layout(showlegend=False, height=340,
                                 margin=dict(l=0,r=0,t=10,b=10))
            st.plotly_chart(fig_rt, use_container_width=True)
        else:
            st.info("Not enough response time data for current filter.")

    st.markdown("---")
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("📈 Cumulative Posts Over Time")
        dated = fdf.dropna(subset=["created_date"]).sort_values("created_date")
        dated["cumulative"] = range(1, len(dated)+1)
        fig_cum = px.line(dated, x="created_date", y="cumulative",
                          color="channel", color_discrete_map=CHANNEL_COLORS,
                          labels={"created_date":"Date","cumulative":"Total Posts"},
                          hover_name="title")
        fig_cum.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=10),
                              legend_title="Channel", showlegend=True)
        st.plotly_chart(fig_cum, use_container_width=True)

    with c4:
        st.subheader("📊 Views Generated Per Month")
        monthly_views = fdf.dropna(subset=["created_date"]).groupby("month")["view_count"].sum().reset_index()
        fig_mv = px.area(monthly_views, x="month", y="view_count",
                         color_discrete_sequence=["#4361EE"],
                         labels={"month":"Month","view_count":"Total Views"})
        fig_mv.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=10))
        st.plotly_chart(fig_mv, use_container_width=True)

    st.markdown("---")

    st.subheader("🗓️ Posting Heatmap by Day of Week & Hour")
    timed = fdf.dropna(subset=["created_date"]).copy()
    timed["dow"]  = timed["created_date"].dt.day_name()
    timed["hour"] = timed["created_date"].dt.hour
    heat = timed.groupby(["dow","hour"]).size().reset_index(name="Posts")
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    heat["dow"] = pd.Categorical(heat["dow"], categories=dow_order, ordered=True)
    heat = heat.sort_values("dow")
    fig_heat = px.density_heatmap(heat, x="hour", y="dow", z="Posts",
                                   color_continuous_scale="Blues",
                                   labels={"hour":"Hour (UTC)","dow":"Day","Posts":"Posts"})
    fig_heat.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=10))
    st.plotly_chart(fig_heat, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# TAB 4 — AUTHORS
# ═══════════════════════════════════════════════════════════
with tab4:
    c1, c2 = st.columns([2, 3])

    with c1:
        st.subheader("🏆 Top Authors by Posts")
        auth = fdf.groupby("author").agg(
            Posts=("id","count"),
            Views=("view_count","sum"),
            Reactions=("reaction_count","sum"),
            Responses=("response_count","sum"),
            Channels=("channel","nunique"),
        ).sort_values("Posts", ascending=False).head(15).reset_index()
        auth.index = range(1, len(auth)+1)
        st.dataframe(auth, use_container_width=True, height=440)

    with c2:
        st.subheader("👁️ Top Authors by Views Generated")
        top_auth_views = auth.nlargest(12, "Views")
        fig_av = px.bar(top_auth_views.sort_values("Views"),
                        x="Views", y="author", orientation="h",
                        color="Posts", color_continuous_scale="Blues",
                        text="Views",
                        labels={"author":"","Views":"Total Views Generated"})
        fig_av.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_av.update_layout(height=440, margin=dict(l=0,r=60,t=10,b=10),
                             coloraxis_colorbar_title="Posts")
        st.plotly_chart(fig_av, use_container_width=True)

    st.markdown("---")
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("🔄 Author Activity by Channel")
        auth_ch = fdf.groupby(["channel","author"]).size().reset_index(name="Posts")
        top_authors = auth_ch.groupby("author")["Posts"].sum().nlargest(10).index
        auth_ch_top = auth_ch[auth_ch["author"].isin(top_authors)]
        fig_ac = px.bar(auth_ch_top, x="author", y="Posts", color="channel",
                        color_discrete_map=CHANNEL_COLORS,
                        labels={"author":"Author","Posts":"# Posts"},
                        barmode="stack")
        fig_ac.update_layout(height=360, margin=dict(l=0,r=0,t=10,b=60),
                             xaxis_tickangle=-35, legend_title="Channel")
        st.plotly_chart(fig_ac, use_container_width=True)

    with c4:
        st.subheader("📐 Post Type per Top Author")
        auth_type = fdf[fdf["author"].isin(top_authors)].groupby(
            ["author","type_label"]).size().reset_index(name="Posts")
        fig_at = px.bar(auth_type, x="Posts", y="author", color="type_label",
                        orientation="h", barmode="stack",
                        color_discrete_sequence=["#4361EE","#F72585","#FFB703"],
                        labels={"author":"","type_label":"Type"})
        fig_at.update_layout(height=360, margin=dict(l=0,r=0,t=10,b=10),
                             legend_title="Post Type")
        st.plotly_chart(fig_at, use_container_width=True)

    st.markdown("---")

    # One-time vs repeat posters
    poster_freq = fdf.groupby("author").size()
    one_time = (poster_freq == 1).sum()
    repeat   = (poster_freq  > 1).sum()
    st.subheader("🔁 Poster Frequency")
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("One-time posters",  one_time)
    pc2.metric("Repeat contributors", repeat)
    pc3.metric("Anonymous posts",    int(fdf["is_anonymous"].sum()))

    fig_freq = px.histogram(poster_freq, nbins=15,
                            color_discrete_sequence=["#4361EE"],
                            labels={"value":"Posts per Author","count":"# Authors"},
                            title="Distribution of Posts per Author")
    fig_freq.update_layout(height=280, margin=dict(l=0,r=0,t=30,b=10), showlegend=False)
    st.plotly_chart(fig_freq, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# TAB 5 — Q&A DEEP DIVE
# ═══════════════════════════════════════════════════════════
with tab5:
    questions = fdf[fdf["type_label"] == "Help / Question"].copy()
    shares    = fdf[fdf["type_label"] == "Share / Resource"].copy()

    st.subheader("❓ Question Analysis")
    qa1, qa2, qa3, qa4 = st.columns(4)
    qa1.metric("Total Questions", len(questions))
    qa2.metric("With Responses",  int(questions["has_responses"].sum()))
    qa3.metric("Unanswered",      int((~questions["has_responses"]).sum()))
    qa4.metric("Avg Views/Question", f"{questions['view_count'].mean():.0f}")

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📌 Most Viewed Questions")
        top_q = questions.nlargest(12, "view_count")[["short_title","channel","view_count","response_count","has_responses"]]
        fig_q = px.bar(top_q.sort_values("view_count"),
                       x="view_count", y="short_title", orientation="h",
                       color="channel", color_discrete_map=CHANNEL_COLORS,
                       text="view_count",
                       labels={"view_count":"Views","short_title":""})
        fig_q.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_q.update_layout(height=440, showlegend=False, margin=dict(l=0,r=50,t=10,b=10))
        st.plotly_chart(fig_q, use_container_width=True)

    with c2:
        st.subheader("🚨 Unanswered Questions (High Views = Pain Points)")
        unanswered = questions[~questions["has_responses"]].nlargest(10, "view_count")
        if len(unanswered):
            fig_un = px.bar(unanswered.sort_values("view_count"),
                            x="view_count", y="short_title", orientation="h",
                            color="channel", color_discrete_map=CHANNEL_COLORS,
                            text="view_count",
                            labels={"view_count":"Views","short_title":""})
            fig_un.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig_un.update_layout(height=440, showlegend=False, margin=dict(l=0,r=50,t=10,b=10))
            st.plotly_chart(fig_un, use_container_width=True)
        else:
            st.success("All questions have responses!")

    st.markdown("---")
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("📣 Questions per Channel")
        q_ch = questions.groupby("channel").agg(
            Questions=("id","count"),
            Unanswered=("has_responses", lambda x: (~x).sum()),
        ).sort_values("Questions", ascending=True).reset_index()
        q_ch["Answered"] = q_ch["Questions"] - q_ch["Unanswered"]
        fig_qch = go.Figure()
        fig_qch.add_bar(x=q_ch["Answered"],   y=q_ch["channel"], orientation="h",
                        name="Answered",   marker_color="#4361EE")
        fig_qch.add_bar(x=q_ch["Unanswered"], y=q_ch["channel"], orientation="h",
                        name="Unanswered", marker_color="#F72585")
        fig_qch.update_layout(barmode="stack", height=380,
                              margin=dict(l=0,r=0,t=10,b=10), legend_title="Status")
        st.plotly_chart(fig_qch, use_container_width=True)

    with c4:
        st.subheader("📤 Shared Resources — Top by Reactions")
        if len(shares):
            top_share = shares.nlargest(10, "reaction_count")[["short_title","channel","reaction_count","view_count"]]
            fig_sh = px.bar(top_share.sort_values("reaction_count"),
                            x="reaction_count", y="short_title", orientation="h",
                            color="channel", color_discrete_map=CHANNEL_COLORS,
                            text="reaction_count",
                            labels={"reaction_count":"Reactions","short_title":""})
            fig_sh.update_layout(height=380, showlegend=False, margin=dict(l=0,r=30,t=10,b=10))
            st.plotly_chart(fig_sh, use_container_width=True)

    st.markdown("---")

    # Response time by channel
    st.subheader("⏳ Avg Response Time by Channel (hours)")
    rt_ch = fdf[fdf["response_hours"] > 0].groupby("channel")["response_hours"].agg(
        Median="median", Mean="mean", Count="count"
    ).round(1).sort_values("Median").reset_index()
    fig_rtch = px.bar(rt_ch, x="channel", y="Median",
                      color="Median", color_continuous_scale="RdYlGn_r",
                      text="Median",
                      labels={"channel":"","Median":"Median Hours to Response"})
    fig_rtch.update_traces(texttemplate="%{text:.0f}h", textposition="outside")
    fig_rtch.update_layout(height=320, coloraxis_showscale=False,
                           margin=dict(l=0,r=0,t=10,b=60), xaxis_tickangle=-35)
    st.plotly_chart(fig_rtch, use_container_width=True)

    st.markdown("---")

    # Full questions table
    with st.expander("📋 All Questions — Full Table"):
        sort_q = st.selectbox("Sort by", ["view_count","response_count","reaction_count","created_date"], key="qsort")
        disp = questions[["title","channel","author","view_count","response_count",
                          "reaction_count","has_responses","created_date"]].sort_values(sort_q, ascending=False)
        disp = disp.rename(columns={"view_count":"views","response_count":"responses",
                                    "reaction_count":"reactions","has_responses":"has_response",
                                    "created_date":"date"})
        st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Key Insights Banner ───────────────────────────────────────────────────────
st.subheader("💡 Key Insights")
i1, i2, i3, i4 = st.columns(4)
top_post    = fdf.loc[fdf["view_count"].idxmax()] if len(fdf) else None
top_channel = fdf.groupby("channel")["view_count"].sum().idxmax() if len(fdf) else "—"
busiest_m   = fdf.groupby("month").size().idxmax() if len(fdf) else "—"
unanswered_pct = int((~questions["has_responses"]).sum() / max(len(questions),1) * 100)

if top_post is not None:
    i1.info(f"**Most Viewed Post**\n\n\"{top_post['title'][:55]}\" — **{top_post['view_count']:,} views**")
i2.success(f"**Most Active Channel**\n\n{top_channel} generated the most total views")
i3.warning(f"**Busiest Month**\n\n{busiest_m} had the most new posts")
i4.error(f"**{unanswered_pct}% of questions** have no responses yet — community support gap")

st.caption("Scraped & analysed by Supritha Kulkarni · CU Boulder MSDS · June 2026")
