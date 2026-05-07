import json
import csv
import re
from pathlib import Path

OUT_DIR = Path(r"C:\Users\Supritha Kulkarni\inscribe_analysis")

raw = json.loads((OUT_DIR / "api_raw.json").read_text(encoding="utf-8"))

# Pull conversations from every mainLayout response (deduplicate by id)
seen = set()
records = []

for entry in raw:
    if "mainLayout" not in entry["url"]:
        continue
    resources = entry["data"].get("enrichedContentResources", [])
    for r in resources:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        records.append({
            "id":               r["id"],
            "title":            r["title"],
            "body":             re.sub(r"<[^>]+>", "", r.get("bodyHTML", "")),
            "author":           r.get("authorName", ""),
            "type":             r.get("conversationType", ""),
            "channel":          r.get("channel", {}).get("name", ""),
            "created_date":     r.get("createdDate", ""),
            "last_response":    r.get("latestResponseDate", ""),
            "last_responder":   r.get("latestResponseAuthorName", ""),
            "view_count":       r.get("viewCount", 0),
            "response_count":   r.get("responseCount", 0),
            "reply_count":      r.get("replyCount", 0),
            "reaction_count":   (r.get("reactionSummary") or {}).get("reactionCount", 0),
            "has_answer":       r.get("hasModeratorOrEndorsedResponse", False),
            "is_anonymous":     r.get("isAnonymous", False),
            "is_archived":      r.get("isArchived", False),
        })

print(f"Extracted {len(records)} conversations")
for r in records[:5]:
    print(f"  [{r['type']}] {r['title'][:60]}  views={r['view_count']} responses={r['response_count']}")

# Save CSV
csv_path = OUT_DIR / "inscribe_conversations.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

# Save JSON
json_path = OUT_DIR / "inscribe_conversations.json"
json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nSaved to:\n  {csv_path}\n  {json_path}")
