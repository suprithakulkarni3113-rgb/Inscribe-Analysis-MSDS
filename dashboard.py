import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
from pathlib import Path
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="InScribe Analysis", page_icon="📚", layout="wide")

OUT = Path(__file__).parent

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    data = json.loads((OUT / "inscribe_conversations.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(data)
    df["view_count"]     = pd.to_numeric(df["view_count"], errors="coerce").fillna(0).astype(int)
    df["response_count"] = pd.to_numeric(df["response_count"], errors="coerce").fillna(0).astype(int)
    df["reaction_count"] = pd.to_numeric(df["reaction_count"], errors="coerce").fillna(0).astype(int)
    df["created_date"]   = pd.to_datetime(df["created_date"], errors="coerce", utc=True)
    df["last_response"]  = pd.to_datetime(df["last_response"], errors="coerce", utc=True)
    df["response_hours"] = (df["last_response"] - df["created_date"]).dt.total_seconds() / 3600
    df["short_title"]    = df["title"].apply(lambda t: t[:50] + "…" if len(str(t)) > 50 else t)
    return df

df = load()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📚 InScribe Community — Conversation Analysis")
st.caption("Data scraped from the InScribe Support community · Built with Python + Streamlit")
st.markdown("---")

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Conversations", len(df))
k2.metric("Total Views", f"{df['view_count'].sum():,}")
k3.metric("Avg Views / Post", f"{df['view_count'].mean():.0f}")
k4.metric("100% Answered", f"{int(df['has_answer'].sum())}/{len(df)}")
k5.metric("Unique Authors", df["author"].nunique())

st.markdown("---")

# ── Row 1: Top questions + views vs responses ─────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("🔥 Top 10 Most Viewed Questions")
    top10 = df.nlargest(10, "view_count").sort_values("view_count")
    fig = px.bar(
        top10, x="view_count", y="short_title", orientation="h",
        labels={"view_count": "Views", "short_title": ""},
        color="view_count", color_continuous_scale="Blues",
        text="view_count"
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=40, t=10, b=10), height=380)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💬 Views vs Responses")
    fig2 = px.scatter(
        df, x="response_count", y="view_count",
        hover_name="title", size="reaction_count",
        size_max=20, color="view_count",
        color_continuous_scale="Oranges",
        labels={"response_count": "Responses", "view_count": "Views"},
    )
    fig2.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=10), height=380)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Row 2: Response time + posts over time ────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("⏱️ Response Time Distribution")
    times = df["response_hours"].dropna()
    fig3 = px.histogram(
        times, nbins=10,
        labels={"value": "Hours to First Response", "count": "Posts"},
        color_discrete_sequence=["#55A868"]
    )
    fig3.add_vline(x=times.mean(), line_dash="dash", line_color="red",
                   annotation_text=f"Mean {times.mean():.0f}h")
    fig3.add_vline(x=times.median(), line_dash="dot", line_color="orange",
                   annotation_text=f"Median {times.median():.0f}h")
    fig3.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=10), height=320)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("📅 Posting Activity Over Time")
    dated = df.dropna(subset=["created_date"]).copy()
    dated["month"] = dated["created_date"].dt.to_period("M").astype(str)
    monthly = dated.groupby("month").size().reset_index(name="posts")
    fig4 = px.bar(monthly, x="month", y="posts", color="posts",
                  color_continuous_scale="Blues",
                  labels={"month": "Month", "posts": "Conversations"})
    fig4.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=10), height=320)
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ── Row 3: Word cloud + author table ─────────────────────────────────────────
col5, col6 = st.columns([2, 3])

with col5:
    st.subheader("☁️ Word Cloud — Topics")
    text = " ".join(df["title"].fillna("") + " " + df["body"].fillna(""))
    wc = WordCloud(width=600, height=320, background_color="white",
                   colormap="Blues", max_words=60).generate(text)
    fig5, ax = plt.subplots(figsize=(6, 3.2))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    st.pyplot(fig5)

with col6:
    st.subheader("👤 Author Activity")
    author_df = df.groupby("author").agg(
        Posts=("title", "count"),
        Total_Views=("view_count", "sum"),
        Total_Responses=("response_count", "sum"),
    ).sort_values("Total_Views", ascending=False).reset_index()
    st.dataframe(author_df, use_container_width=True, height=320)

st.markdown("---")

# ── Full data table ───────────────────────────────────────────────────────────
with st.expander("📋 View Full Dataset"):
    display_cols = ["title", "author", "view_count", "response_count",
                    "reaction_count", "has_answer", "channel", "created_date"]
    st.dataframe(df[display_cols].sort_values("view_count", ascending=False),
                 use_container_width=True)

st.caption("Scraped & analysed by Supritha Kulkarni · May 2026")
