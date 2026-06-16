"""
InScribe Colorado Community Scraper — v5
Channels are shown as grid cards (not sidebar links).
Clicks each card by channel name text, waits for navigation,
then scrolls the conversations list and captures API responses.
"""

import time
import json
import csv
import re
import html
from pathlib import Path
from playwright.sync_api import sync_playwright

ORG      = "colorado"
COMM_ID  = "6754110229507555"
BASE_URL = f"https://inscribe.education/main/{ORG}/{COMM_ID}"
OUT_DIR  = Path(r"C:\Users\Supritha Kulkarni\colorado_analysis")


def clean(text):
    text = html.unescape(str(text or ""))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def extract_conversations(data, channel_name, channel_slug):
    candidates = []
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        for key in ["enrichedContentResources", "allContent", "conversations",
                    "results", "items", "posts", "content", "data"]:
            val = data.get(key)
            if isinstance(val, list) and val:
                candidates = val
                break
        if not candidates:
            for val in data.values():
                if isinstance(val, dict):
                    for key in ["enrichedContentResources", "allContent",
                                "conversations", "results", "items"]:
                        inner = val.get(key)
                        if isinstance(inner, list) and inner:
                            candidates = inner
                            break

    convos = []
    for item in candidates:
        if isinstance(item, dict) and item.get("id"):
            item["_channel_name"] = channel_name
            item["_channel_slug"] = channel_slug
            convos.append(item)
    return convos


def scrape():
    session_file = OUT_DIR / "session.json"
    if not session_file.exists():
        print("No session.json — run save_session.py first.")
        return

    intercepted = []
    all_urls    = []   # every URL fired by inscribe, for debugging

    def on_response(response):
        try:
            if "inscribe.education" not in response.url:
                return
            # Log every URL regardless of content type
            ct = response.headers.get("content-type", "")
            if "json" in ct or "javascript" in ct or "text" in ct:
                try:
                    data = response.json()
                    intercepted.append({"url": response.url, "data": data})
                except Exception:
                    pass
            # Always log the URL so we can see what's firing
            all_urls.append({"url": response.url, "ct": ct, "status": response.status})
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(session_file),
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.on("response", on_response)

        # ── 1. Open channels page ─────────────────────────────────────────
        print("Loading channels page...")
        page.goto(f"{BASE_URL}/channels", wait_until="networkidle", timeout=30000)
        time.sleep(4)

        # Dump all links so we can see what hrefs exist
        all_hrefs = page.eval_on_selector_all("a", "els => els.map(e => [e.href, e.innerText.trim().slice(0,60)])")
        print("\nAll links on channels page:")
        for href, text in all_hrefs:
            if href:
                print(f"  {text[:40]:40s} → {href}")

        # ── 2. Discover channels ──────────────────────────────────────────
        channels = []
        seen_slugs = set()

        # Try every <a> href on the page
        for href, text in all_hrefs:
            # Match any href pattern with /channels/SLUG
            m = re.search(r"/channels/([^/?#\s]+)", href)
            if m:
                slug = m.group(1)
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    channels.append({"slug": slug, "name": text.strip() or slug, "href": href})

        # Also check from API responses
        for entry in intercepted:
            data = entry["data"]
            if not isinstance(data, dict):
                continue
            for key in ["channels", "myChannels", "enrolledChannels", "communityChannels"]:
                lst = data.get(key)
                if isinstance(lst, list):
                    for ch in lst:
                        if isinstance(ch, dict):
                            slug = ch.get("slugName") or ch.get("slug", "")
                            name = ch.get("name", slug)
                            if slug and slug not in seen_slugs:
                                seen_slugs.add(slug)
                                channels.append({"slug": slug, "name": name, "href": ""})

        print(f"\nDiscovered {len(channels)} channel(s):")
        for ch in channels:
            print(f"  [{ch['slug']:35s}] {ch['name']}")

        if not channels:
            # Try clicking each visible card by text
            # Get all text visible on page that look like channel names
            print("\nFallback: reading channel card text from page...")
            page.screenshot(path=str(OUT_DIR / "debug_channels.png"))
            # Try to get channel names from the card headings
            headings = page.eval_on_selector_all(
                "h1,h2,h3,h4,h5,h6,p,span,div",
                "els => els.map(e => e.innerText.trim()).filter(t => t.length > 0 && t.length < 60)"
            )
            print("Text found on page:", headings[:30])
            browser.close()
            return

        # ── 3. Scrape each channel ────────────────────────────────────────
        all_conversations = []
        global_seen_ids   = set()

        for ch in channels:
            slug = ch["slug"]
            name = ch["name"]
            print(f"\n{'─'*60}")
            print(f"Scraping: {name}  (slug={slug})")

            pre      = len(intercepted)
            pre_urls = len(all_urls)

            # Real URL pattern: /main/org/comm/SLUG/all-content
            ch_url = ch["href"] if ch["href"] else f"{BASE_URL}/{slug}/all-content"

            print(f"  → {ch_url}")
            try:
                page.goto(ch_url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"  load timeout (continuing): {e}")

            time.sleep(6)
            print(f"  Current URL: {page.url}")

            # Scroll to trigger lazy-loading and content_url_template capture
            page.mouse.click(700, 500)
            stale = 0
            prev  = len(intercepted)
            for i in range(30):
                page.mouse.wheel(0, 2500)
                time.sleep(1.5)
                cur = len(intercepted)
                if cur == prev:
                    stale += 1
                    if stale >= 5:
                        break
                else:
                    stale = 0
                prev = cur
                if (i + 1) % 5 == 0:
                    print(f"  scroll {i+1}: {len(intercepted) - pre} new API responses")

            # Find the exact mainLayout content URL the page fired (batchNumber=1)
            # e.g. ...&channelSlugName=dtsa-5001&contentId=0&batchNumber=1&preferredTimezone=...
            new_entries = intercepted[pre:]
            content_url_template = None
            for entry in new_entries:
                url = entry["url"]
                # Match any mainLayout/data call that has batchNumber and channelSlugName
                if ("mainLayout/data" in url and "batchNumber=1" in url
                        and ("channelSlugName" in url or "channel=" in url)):
                    content_url_template = re.sub(r"&batchNumber=\d+", "", url)
                    print(f"  Found content URL template: ...{content_url_template[-100:]}")
                    break

            ch_convos = []

            # Extract batch 1 from the already-captured intercept
            for entry in new_entries:
                for c in extract_conversations(entry["data"], name, slug):
                    cid = c.get("id")
                    if cid not in global_seen_ids:
                        global_seen_ids.add(cid)
                        ch_convos.append(c)
            if ch_convos:
                print(f"  Intercept gave {len(ch_convos)} posts")

            # Replay the exact URL with batchNumber=2,3,... to get remaining pages
            if content_url_template:
                for batch in range(2, 50):
                    url = f"{content_url_template}&batchNumber={batch}"
                    try:
                        resp = page.request.get(url, timeout=12000)
                        if resp.status != 200:
                            break
                        data = resp.json()
                        found = extract_conversations(data, name, slug)
                        new   = [c for c in found if c.get("id") not in global_seen_ids]
                        if not new:
                            break
                        for c in new:
                            global_seen_ids.add(c.get("id"))
                            ch_convos.append(c)
                        print(f"  batch {batch}: +{len(new)}")
                    except Exception as e:
                        print(f"  batch {batch} error: {e}")
                        break
            else:
                # Fallback: try channelSlugName parameter directly
                for batch in range(1, 50):
                    url = (
                        f"https://inscribe.education/views/mainLayout/data"
                        f"?org={ORG}&comm={COMM_ID}"
                        f"&channelSlugName={slug}&contentId=0&batchNumber={batch}"
                        f"&preferredTimezone=America%2FDenver"
                    )
                    try:
                        resp = page.request.get(url, timeout=12000)
                        if resp.status != 200:
                            break
                        data = resp.json()
                        found = extract_conversations(data, name, slug)
                        new   = [c for c in found if c.get("id") not in global_seen_ids]
                        if not new and batch > 1:
                            break
                        for c in new:
                            global_seen_ids.add(c.get("id"))
                            ch_convos.append(c)
                        if new:
                            print(f"  fallback batch {batch}: +{len(new)}")
                    except Exception:
                        break

            print(f"  → {len(ch_convos)} conversations in '{name}'")
            all_conversations.extend(ch_convos)

        browser.close()

    # ── Debug dump ─────────────────────────────────────────────────────────
    debug = [{"url": e["url"], "keys": list(e["data"].keys())
              if isinstance(e["data"], dict) else type(e["data"]).__name__}
             for e in intercepted]
    (OUT_DIR / "debug_api.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(f"\nDebug: {len(intercepted)} total API calls → debug_api.json")
    print(f"Total unique conversations: {len(all_conversations)}")

    if not all_conversations:
        print("Nothing captured. Paste the link output above so I can fix the URL pattern.")
        return

    (OUT_DIR / "raw_conversations.json").write_text(
        json.dumps(all_conversations, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    records = []
    for r in all_conversations:
        records.append({
            "id":             r.get("id"),
            "channel":        r.get("_channel_name", ""),
            "title":          clean(r.get("title", "")),
            "body":           clean(r.get("bodyHTML", "") or r.get("body", "")),
            "author":         r.get("authorName", ""),
            "type":           r.get("conversationType", ""),
            "created_date":   r.get("createdDate", ""),
            "last_response":  r.get("latestResponseDate", ""),
            "last_responder": r.get("latestResponseAuthorName", ""),
            "view_count":     r.get("viewCount", 0),
            "response_count": r.get("responseCount", 0),
            "reply_count":    r.get("replyCount", 0),
            "reaction_count": (r.get("reactionSummary") or {}).get("reactionCount", 0),
            "has_answer":     r.get("hasModeratorOrEndorsedResponse", False),
            "is_anonymous":   r.get("isAnonymous", False),
        })

    csv_path = OUT_DIR / "conversations.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {csv_path}")
    print("\nTop 5 by views:")
    for r in sorted(records, key=lambda x: x["view_count"], reverse=True)[:5]:
        print(f"  [{r['channel']:25s}] {r['title'][:55]}  views={r['view_count']}")


if __name__ == "__main__":
    scrape()
