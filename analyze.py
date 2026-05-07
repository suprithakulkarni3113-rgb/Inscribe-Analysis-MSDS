import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from wordcloud import WordCloud
from datetime import datetime
from pathlib import Path

OUT = Path(r"C:\Users\Supritha Kulkarni\inscribe_analysis")
data = json.loads((OUT / "inscribe_conversations.json").read_text(encoding="utf-8"))
df = pd.DataFrame(data)

df["view_count"]      = pd.to_numeric(df["view_count"], errors="coerce").fillna(0).astype(int)
df["response_count"]  = pd.to_numeric(df["response_count"], errors="coerce").fillna(0).astype(int)
df["reaction_count"]  = pd.to_numeric(df["reaction_count"], errors="coerce").fillna(0).astype(int)
df["created_date"]    = pd.to_datetime(df["created_date"], errors="coerce")
df["last_response"]   = pd.to_datetime(df["last_response"], errors="coerce")
df["response_hours"]  = (df["last_response"] - df["created_date"]).dt.total_seconds() / 3600

plt.rcParams.update({"figure.dpi": 120, "font.size": 10})

# ── 1. Summary stats ─────────────────────────────────────────────────────────
print("=" * 55)
print("INSCRIBE CONVERSATIONS — SUMMARY")
print("=" * 55)
print(f"Total conversations : {len(df)}")
print(f"Total views         : {df['view_count'].sum():,}")
print(f"Avg views/post      : {df['view_count'].mean():.0f}")
print(f"Median views        : {df['view_count'].median():.0f}")
print(f"Total responses     : {df['response_count'].sum()}")
print(f"Posts with answer   : {df['has_answer'].sum()} / {len(df)}")
print(f"Unique authors      : {df['author'].nunique()}")
print(f"Avg response time   : {df['response_hours'].mean():.1f} hours")
print()

# ── 2. Top 10 by views ───────────────────────────────────────────────────────
top = df.nlargest(10, "view_count")[["title", "view_count", "response_count"]]
print("TOP 10 BY VIEWS:")
for _, r in top.iterrows():
    print(f"  {r['view_count']:>5,}  {r['title'][:50]}")

# ── 3. Chart: Top questions by views ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
top10 = df.nlargest(10, "view_count").sort_values("view_count")
labels = [t[:45] + "…" if len(t) > 45 else t for t in top10["title"]]
bars = ax.barh(labels, top10["view_count"], color="#4C72B0")
ax.bar_label(bars, fmt="%d", padding=4)
ax.set_xlabel("View Count")
ax.set_title("Top 10 Most Viewed Conversations")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.tight_layout()
plt.savefig(OUT / "chart_top_views.png")
plt.close()
print("\nSaved: chart_top_views.png")

# ── 4. Chart: Views vs Responses scatter ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(df["response_count"], df["view_count"], s=80, color="#DD8452", alpha=0.8)
for _, r in df.iterrows():
    ax.annotate(r["title"][:25], (r["response_count"], r["view_count"]),
                fontsize=7, alpha=0.7, xytext=(4, 2), textcoords="offset points")
ax.set_xlabel("Number of Responses")
ax.set_ylabel("View Count")
ax.set_title("Views vs. Responses")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.tight_layout()
plt.savefig(OUT / "chart_views_vs_responses.png")
plt.close()
print("Saved: chart_views_vs_responses.png")

# ── 5. Chart: Response time distribution ─────────────────────────────────────
times = df["response_hours"].dropna()
if len(times) > 0:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(times, bins=10, color="#55A868", edgecolor="white")
    ax.axvline(times.mean(), color="red", linestyle="--", label=f"Mean: {times.mean():.1f}h")
    ax.axvline(times.median(), color="orange", linestyle="--", label=f"Median: {times.median():.1f}h")
    ax.set_xlabel("Hours to First Response")
    ax.set_ylabel("Count")
    ax.set_title("Response Time Distribution")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "chart_response_time.png")
    plt.close()
    print("Saved: chart_response_time.png")

# ── 6. Chart: Posts over time ─────────────────────────────────────────────────
dated = df.dropna(subset=["created_date"]).copy()
if len(dated) > 0:
    dated["month"] = dated["created_date"].dt.to_period("M")
    monthly = dated.groupby("month").size()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([str(m) for m in monthly.index], monthly.values, color="#4C72B0")
    ax.set_xlabel("Month")
    ax.set_ylabel("Conversations")
    ax.set_title("Conversations Posted Per Month")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(OUT / "chart_posts_over_time.png")
    plt.close()
    print("Saved: chart_posts_over_time.png")

# ── 7. Word cloud from titles ─────────────────────────────────────────────────
text = " ".join(df["title"].fillna("") + " " + df["body"].fillna(""))
wc = WordCloud(width=800, height=400, background_color="white",
               colormap="Blues", max_words=60).generate(text)
plt.figure(figsize=(10, 5))
plt.imshow(wc, interpolation="bilinear")
plt.axis("off")
plt.title("Word Cloud — Conversation Topics")
plt.tight_layout()
plt.savefig(OUT / "chart_wordcloud.png")
plt.close()
print("Saved: chart_wordcloud.png")

# ── 8. Author activity ────────────────────────────────────────────────────────
author_stats = df.groupby("author").agg(
    posts=("title", "count"),
    total_views=("view_count", "sum"),
    total_responses=("response_count", "sum")
).sort_values("total_views", ascending=False)
print("\nAUTHOR ACTIVITY:")
print(author_stats.to_string())

print("\nAll charts saved to:", OUT)
