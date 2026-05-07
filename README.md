# InScribe Community — Conversation Analysis

An end-to-end data pipeline that scrapes, processes, and visualizes conversation data from an InScribe education community. Built as a portfolio project demonstrating web scraping, data analysis, and interactive dashboard development.

---

## Live Dashboard

> 🚀 [View on Streamlit Cloud](#) *(deploy link goes here)*

---

## Project Overview

| | |
|---|---|
| **Data Source** | InScribe Education community (conversations page) |
| **Records Scraped** | 19 conversations |
| **Total Views** | 26,125 across all posts |
| **Top Question** | "delete a conversation?" — 5,548 views |
| **Answer Rate** | 100% — all posts have a moderator response |

---

## Key Insights

- 📈 **"delete a conversation?"** is the most viewed question with **5,548 views** — a clear pain point for users
- ⏱️ Average response time is high, skewed by a few very old posts; most questions are answered within hours
- 👤 **17 unique authors** — nearly all one-time posters, indicating the community serves as a support channel rather than a recurring discussion forum
- 📱 Mobile app navigation and notification settings are the most common topics
- ✅ **100% of posts** have a moderator or endorsed response

---

## Tech Stack

| Tool | Purpose |
|---|---|
| `Playwright` | Browser automation — scrapes JavaScript-rendered pages |
| `Python` | Data extraction, cleaning, analysis |
| `Pandas` | Data manipulation |
| `Plotly` | Interactive charts |
| `Matplotlib` + `WordCloud` | Static visualizations |
| `Streamlit` | Interactive web dashboard |

---

## Project Structure

```
inscribe_analysis/
├── scraper.py                  # Playwright scraper (API interception)
├── extract.py                  # Parses raw API responses into clean CSV/JSON
├── analyze.py                  # EDA + static chart generation
├── dashboard.py                # Streamlit dashboard
├── inscribe_conversations.csv  # Clean dataset
├── inscribe_conversations.json # Clean dataset (JSON)
├── chart_top_views.png
├── chart_views_vs_responses.png
├── chart_response_time.png
├── chart_posts_over_time.png
├── chart_wordcloud.png
└── requirements.txt
```

---

## How to Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/suprithakulkarni3113-rgb/Inscribe-Analysis-MSDS.git
cd Inscribe-Analysis-MSDS
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

**3. Run the dashboard**
```bash
streamlit run dashboard.py
```

**4. Re-scrape data** *(optional — requires access to the InScribe community)*
```bash
python scraper.py   # opens Edge, scrapes API responses
python extract.py   # parses responses into CSV/JSON
python analyze.py   # regenerates charts
```

---

## Dashboard Preview

| Chart | Description |
|---|---|
| Top 10 by Views | Bar chart of most viewed conversations |
| Views vs Responses | Scatter plot showing engagement patterns |
| Response Time | Distribution of time-to-first-response |
| Monthly Activity | Posting trends over time |
| Word Cloud | Most common topics across all conversations |
| Author Activity | Per-author post and view counts |

---

## Author

**Supritha Kulkarni** — MS Data Science student  
[GitHub](https://github.com/suprithakulkarni3113-rgb)
