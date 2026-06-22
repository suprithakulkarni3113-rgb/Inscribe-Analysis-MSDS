"""
CU Boulder MSDS — InScribe Community Analysis Dashboard
"""
import html, re
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
/* Page background */
.stApp { background-color: #0f172a; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #1e293b; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* KPI cards */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 16px 20px;
}
[data-testid="metric-container"] label { color: #94a3b8 !important; font-size: 0.78rem; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important; font-size: 1.7rem; font-weight: 700;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] { color: #38bdf8 !important; }

/* Headings */
h1 { color: #f1f5f9 !important; font-weight: 800 !important; letter-spacing: -0.5px; }
h2 { color: #e2e8f0 !important; font-weight: 700 !important; margin-top: 0.2rem !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }

/* Body text & captions */
p, .stMarkdown p { color: #94a3b8 !important; }
.stCaption, [data-testid="stCaptionContainer"] p { color: #64748b !important; }

/* Tabs */
[data-testid="stTabs"] button {
    color: #94a3b8 !important;
    font-weight: 600;
    border-radius: 8px 8px 0 0;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
}

/* Divider */
hr { border-color: #1e293b !important; }

/* Dataframe */
[data-testid="stDataFrame"] { background: #1e293b; border-radius: 10px; }

/* Expander */
[data-testid="stExpander"] { background: #1e293b; border-radius: 10px; border: 1px solid #334155; }

/* Info/warning/error boxes */
[data-testid="stAlert"] { border-radius: 10px; border: none; }
.stAlert [data-testid="stMarkdownContainer"] p { color: inherit !important; }

/* Block container */
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px; }
</style>""", unsafe_allow_html=True)

TEMPLATE = "plotly_dark"
BG       = "rgba(0,0,0,0)"   # transparent — inherits page bg
GRID     = "#1e293b"
ACCENT   = "#38bdf8"

OUT = Path(__file__).parent

CC = {
    "General":                                                    "#38bdf8",
    "Machine Learning":                                           "#f472b6",
    "Statistical Modeling for Data Science":                      "#a78bfa",
    "Data Mining Foundations and Practice":                       "#34d399",
    "Data Science Foundations: Statistical Inference":            "#fbbf24",
    "Data Science Methods for Quality Improvement":               "#4ade80",
    "Vital Skills":                                               "#fb923c",
    "Databases":                                                  "#818cf8",
    "Text Market Analytics":                                      "#f87171",
    "Bayesian Statistics":                                        "#2dd4bf",
    "Modeling and Predicting Climate Anomalies":                  "#a3e635",
    "Data Science Foundations: Data Structures and Algorithms":   "#c084fc",
    "High Performance and Parallel Computing":                    "#fdba74",
    "Computer Vision":                                            "#67e8f9",
    "Industry Collaboration: IBM Capstone Project":               "#fde68a",
    "Statistical Learning for Data Science":                      "#86efac",
    "Effective Communication":                                    "#cbd5e1",
    "NLP: Natural Language Processing":                           "#7dd3fc",
    "Deep Learning Applications for Computer Vision":             "#d8b4fe",
    "Security and Ethical Hacking":                               "#fca5a5",
    "Internet Policy":                                            "#fcd34d",
}

def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(t or "")))).strip()

LABEL = "#e2e8f0"   # bright enough to read on dark bg
MUTED = "#94a3b8"   # secondary text

def chart_layout(fig, height=380, xangle=0, legend=True):
    axis = dict(
        gridcolor=GRID,
        zerolinecolor=GRID,
        tickfont=dict(color=LABEL, size=11),
        title_font=dict(color=LABEL, size=12),
    )
    fig.update_layout(
        template=TEMPLATE,
        paper_bgcolor=BG, plot_bgcolor=BG,
        height=height,
        margin=dict(l=0, r=10, t=16, b=10),
        font=dict(family="Inter, sans-serif", color=LABEL),
        xaxis={**axis, "tickangle": xangle},
        yaxis=axis,
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=LABEL)),
    )
    fig.update_traces(textfont=dict(color=LABEL))
    return fig

@st.cache_data
def load():
    df = pd.read_csv(OUT / "conversations.csv")
    for col in ["title", "body", "author", "channel", "last_responder"]:
        df[col] = df[col].apply(clean)
    for col in ["view_count", "response_count", "reply_count", "reaction_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["created_date"]  = pd.to_datetime(df["created_date"],  errors="coerce", utc=True)
    df["last_response"] = pd.to_datetime(df["last_response"], errors="coerce", utc=True)
    df.loc[df["last_response"].dt.year < 2000, "last_response"] = pd.NaT
    df["response_hours"] = (df["last_response"] - df["created_date"]).dt.total_seconds() / 3600
    df["month"]         = df["created_date"].dt.to_period("M").astype(str)
    df["type_label"]    = df["type"].map({
        "helpQuestion": "Help / Question",
        "sharePost":    "Share / Resource",
        "liveSession":  "Live Session",
    }).fillna(df["type"])
    df["short_title"]   = df["title"].apply(lambda t: t[:55] + "…" if len(t) > 55 else t)
    df["has_responses"] = df["response_count"] > 0
    df["is_anonymous"]  = df["is_anonymous"].astype(str).str.lower().isin(["true","1","yes"])
    return df

df = load()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    sel_ch   = st.selectbox("Channel", ["All Channels"] + sorted(df["channel"].dropna().unique()))
    sel_type = st.selectbox("Post Type", ["All Types"] + sorted(df["type_label"].dropna().unique()))
    all_m    = sorted(df["month"].dropna().unique())
    sel_m    = st.multiselect("Month(s)", all_m, default=all_m)
    st.caption("Data: Dec 2025 – Jun 2026")

fdf = df.copy()
if sel_ch   != "All Channels": fdf = fdf[fdf["channel"] == sel_ch]
if sel_type != "All Types":    fdf = fdf[fdf["type_label"] == sel_type]
if sel_m:                      fdf = fdf[fdf["month"].isin(sel_m)]

questions = fdf[fdf["type_label"] == "Help / Question"]
shares    = fdf[fdf["type_label"] == "Share / Resource"]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("CU Boulder MSDS — InScribe Community Analysis")
st.caption("Analysing whether InScribe is effectively supporting students · Dec 2025 – Jun 2026")
st.divider()

# ── KPIs ─────────────────────────────────────────────────────────────────────
total_q     = len(questions)
responded_q = int(questions["has_responses"].sum())
resp_rate   = int(responded_q / max(total_q, 1) * 100)
rt_vals     = fdf["response_hours"].dropna()
rt_vals     = rt_vals[rt_vals > 0]
med_rt      = rt_vals.median() if len(rt_vals) else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Posts",         f"{len(fdf):,}")
k2.metric("Total Views",         f"{fdf['view_count'].sum():,}")
k3.metric("Questions Asked",     f"{total_q:,}")
k4.metric("Response Rate",       f"{resp_rate}%")
k5.metric("Median Response Time",f"{med_rt:.0f} hrs")
k6.metric("Channels w/ Posts",   f"{fdf['channel'].nunique()} / 22")

st.divider()

# ══ Tabs ══════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "❓  Is InScribe Helping?",
    "📌  What Students Ask",
    "📊  Channels & Activity",
    "👤  Contributors",
])

# ════════════════════════════════════════════════
# TAB 1 — IS INSCRIBE HELPING?
# ════════════════════════════════════════════════
with tab1:
    unans_pct   = 100 - resp_rate
    top_unans   = questions[~questions["has_responses"]].nlargest(1, "view_count")
    pain_title  = top_unans.iloc[0]["title"][:55] if len(top_unans) else "—"
    pain_views  = int(top_unans.iloc[0]["view_count"]) if len(top_unans) else 0

    b1, b2, b3 = st.columns(3)
    b1.info(    f"**{resp_rate}%** of questions received at least one community response.")
    b2.warning( f"**{unans_pct}%** of questions are still unanswered — a clear support gap.")
    b3.error(   f"Top unanswered: **\"{pain_title}\"** — {pain_views:,} views, zero replies.")

    st.markdown(" ")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Answered vs Unanswered per Channel")
        st.caption("How well is each channel's community responding?")
        q_ch = questions.groupby("channel").agg(
            Questions=("id","count"),
            Unanswered=("has_responses", lambda x: (~x).sum()),
        ).reset_index()
        q_ch["Answered"] = q_ch["Questions"] - q_ch["Unanswered"]
        q_ch = q_ch.sort_values("Questions", ascending=True)

        fig = go.Figure()
        fig.add_bar(x=q_ch["Answered"],   y=q_ch["channel"], orientation="h",
                    name="Answered",   marker_color="#38bdf8", marker_opacity=0.9,
                    textfont=dict(color=LABEL))
        fig.add_bar(x=q_ch["Unanswered"], y=q_ch["channel"], orientation="h",
                    name="Unanswered", marker_color="#f87171", marker_opacity=0.9,
                    textfont=dict(color=LABEL))
        fig.update_layout(barmode="stack",
                          legend=dict(orientation="h", y=-0.08, bgcolor="rgba(0,0,0,0)",
                                      font=dict(color=LABEL)))
        chart_layout(fig, height=440, legend=True)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### High-View Unanswered Questions")
        st.caption("Many students had these questions — nobody answered them.")
        unans_df = questions[~questions["has_responses"]].nlargest(10, "view_count")
        if len(unans_df):
            fig2 = px.bar(
                unans_df.sort_values("view_count"),
                x="view_count", y="short_title", orientation="h",
                color="channel", color_discrete_map=CC,
                text="view_count",
                labels={"view_count":"Views","short_title":""},
            )
            fig2.update_traces(texttemplate="%{text:,}", textposition="outside",
                               marker_opacity=0.85)
            chart_layout(fig2, height=440, legend=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("All questions have at least one response!")

    st.divider()

    st.markdown("#### Median Response Time by Channel")
    st.caption("How quickly students get help. Shorter bar = faster community support.")
    rt_ch = (
        fdf[fdf["response_hours"] > 0]
        .groupby("channel")["response_hours"]
        .median().round(1).reset_index()
        .rename(columns={"response_hours": "Median Hours"})
        .sort_values("Median Hours", ascending=True)
    )
    fig3 = px.bar(
        rt_ch, x="Median Hours", y="channel", orientation="h",
        color="Median Hours", color_continuous_scale="RdYlGn_r",
        text="Median Hours",
        labels={"channel": "", "Median Hours": "Median hrs to First Response"},
    )
    fig3.update_traces(
        texttemplate="%{text:.0f}h", textposition="outside",
        textfont=dict(color=LABEL, size=11), marker_opacity=0.85,
    )
    fig3.update_layout(
        coloraxis_showscale=False,
        yaxis=dict(tickfont=dict(color=LABEL, size=11), title_font=dict(color=LABEL)),
        xaxis=dict(tickfont=dict(color=LABEL, size=11), title_font=dict(color=LABEL),
                   gridcolor=GRID),
    )
    chart_layout(fig3, height=340, legend=False)
    st.plotly_chart(fig3, use_container_width=True)

# ════════════════════════════════════════════════
# TAB 2 — WHAT STUDENTS ASK
# ════════════════════════════════════════════════
with tab2:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("#### Top 12 Most Viewed Questions")
        st.caption("High views = many students shared the same doubt.")
        top_q = questions.nlargest(12, "view_count").sort_values("view_count")
        fig = px.bar(
            top_q, x="view_count", y="short_title", orientation="h",
            color="channel", color_discrete_map=CC,
            text="view_count",
            labels={"view_count":"Views","short_title":""},
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside",
                          marker_opacity=0.85)
        chart_layout(fig, height=480, legend=True)
        fig.update_layout(legend_title="Channel")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### What Are Students Posting?")
        type_df = fdf.groupby("type_label").size().reset_index(name="Count")
        fig2 = px.pie(
            type_df, names="type_label", values="Count",
            color_discrete_map={
                "Help / Question":  "#38bdf8",
                "Share / Resource": "#4ade80",
                "Live Session":     "#fbbf24",
            },
            hole=0.55,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label",
                           textfont_size=12, marker=dict(line=dict(color="#0f172a", width=2)))
        fig2.update_layout(showlegend=False, height=260,
                           margin=dict(l=0,r=0,t=10,b=0),
                           template=TEMPLATE, paper_bgcolor=BG)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Top Shared Resources")
        st.caption("Most reacted community tips & tools.")
        if len(shares):
            top_sh = shares.nlargest(5, "reaction_count")
            for _, row in top_sh.iterrows():
                st.markdown(
                    f"<div style='background:#1e293b;border-radius:8px;"
                    f"padding:10px 14px;margin-bottom:8px;border-left:3px solid #38bdf8'>"
                    f"<span style='color:#e2e8f0;font-size:0.85rem;font-weight:600'>"
                    f"{row['short_title']}</span><br>"
                    f"<span style='color:#64748b;font-size:0.75rem'>"
                    f"👍 {row['reaction_count']} reactions &nbsp;·&nbsp; 👁 {row['view_count']:,} views</span>"
                    f"</div>", unsafe_allow_html=True
                )

    st.divider()

    st.markdown("#### Word Cloud — What Students Talk About Most")
    st.caption("Built from question titles and post bodies across all channels.")
    text = " ".join(questions["title"].fillna("") + " " + questions["body"].fillna(""))
    stopwords = {
        "the","a","an","and","or","in","of","to","is","it","for","i","this","that",
        "my","me","we","be","with","are","on","have","has","was","but","from","as",
        "so","if","by","at","not","they","their","them","its","our","you","your",
        "http","https","www","com","just","can","do","all","any","also","would",
        "could","should","will","been","than","then","when","where","how","what",
        "which","who","there","here","one","get","got","use","using","used",
        "am","im","hi","hey","thanks","thank","anyone","ll","ve","re",
    }
    if text.strip():
        wc = WordCloud(
            width=1400, height=400, background_color="#0f172a",
            colormap="Blues", max_words=80,
            stopwords=stopwords, collocations=True,
        ).generate(text)
        fig_wc, ax = plt.subplots(figsize=(14, 4))
        fig_wc.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)
        st.pyplot(fig_wc)

# ════════════════════════════════════════════════
# TAB 3 — CHANNELS & ACTIVITY
# ════════════════════════════════════════════════
with tab3:
    c1, c2 = st.columns([2, 3])

    with c1:
        st.markdown("#### Posts per Channel")
        ch_df = fdf.groupby("channel").size().reset_index(name="Posts").sort_values("Posts", ascending=True)
        fig = px.bar(
            ch_df, x="Posts", y="channel", orientation="h",
            color="channel", color_discrete_map=CC, text="Posts",
            labels={"channel":"","Posts":"# Posts"},
        )
        fig.update_traces(textposition="outside", marker_opacity=0.85)
        chart_layout(fig, height=500, legend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### Monthly Activity")
        st.caption("How community engagement evolves month over month.")
        monthly = fdf.groupby(["month","type_label"]).size().reset_index(name="Posts")
        fig2 = px.bar(
            monthly, x="month", y="Posts", color="type_label",
            color_discrete_map={
                "Help / Question":  "#38bdf8",
                "Share / Resource": "#4ade80",
                "Live Session":     "#fbbf24",
            },
            barmode="stack",
            labels={"month":"","Posts":"Posts","type_label":""},
        )
        fig2.update_traces(marker_opacity=0.85)
        fig2.update_layout(legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)"),
                           xaxis_tickangle=-30)
        chart_layout(fig2, height=280, legend=True)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Channel Summary")
        ch_table = fdf.groupby("channel").agg(
            Posts=("id","count"),
            Views=("view_count","sum"),
            Questions=("type_label", lambda x: (x=="Help / Question").sum()),
            Unanswered=("has_responses", lambda x: (~x).sum()),
            Authors=("author","nunique"),
        ).sort_values("Posts", ascending=False).reset_index()
        ch_table["Response Rate"] = (
            (ch_table["Questions"] - ch_table["Unanswered"])
            / ch_table["Questions"].replace(0,1) * 100
        ).round(0).astype(int).astype(str) + "%"
        st.dataframe(
            ch_table.rename(columns={"channel":"Channel","Views":"Total Views"}),
            use_container_width=True, hide_index=True, height=240,
        )

# ════════════════════════════════════════════════
# TAB 4 — CONTRIBUTORS
# ════════════════════════════════════════════════
with tab4:
    poster_freq = fdf.groupby("author").size()
    one_time    = int((poster_freq == 1).sum())
    repeat      = int((poster_freq  > 1).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Unique Authors",       fdf["author"].nunique())
    m2.metric("One-time Posters",     one_time)
    m3.metric("Repeat Contributors",  repeat)
    m4.metric("Anonymous Posts",      int(fdf["is_anonymous"].sum()))

    st.caption("Most students post once — InScribe is used as a help desk, not an ongoing community forum.")
    st.markdown(" ")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Top Authors by Posts")
        auth = (
            fdf.groupby("author").agg(
                Posts=("id","count"),
                Views=("view_count","sum"),
                Reactions=("reaction_count","sum"),
                Channels=("channel","nunique"),
            ).sort_values("Posts", ascending=False).head(15).reset_index()
        )
        auth.index = range(1, len(auth)+1)
        st.dataframe(auth, use_container_width=True, height=460)

    with c2:
        st.markdown("#### Who Drives the Most Views?")
        st.caption("Authors whose posts attract the most student attention.")
        top_v = auth.nlargest(12, "Views").sort_values("Views")
        fig = px.bar(
            top_v, x="Views", y="author", orientation="h",
            color="Posts", color_continuous_scale="Blues",
            text="Views",
            labels={"author":"","Views":"Total Views Generated"},
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside",
                          marker_opacity=0.9)
        fig.update_layout(coloraxis_colorbar_title="Posts",
                          coloraxis_colorbar=dict(
                              tickfont=dict(color=LABEL),
                              title=dict(font=dict(color=LABEL)),
                          ))
        chart_layout(fig, height=460, legend=False)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Scraped & analysed by Supritha Kulkarni · CU Boulder MSDS · June 2026 · Built with Python + Streamlit")
