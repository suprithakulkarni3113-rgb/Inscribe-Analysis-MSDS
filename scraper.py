import time
import json
import csv
import subprocess
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://inscribe.education/main/inscribe/4800117945139200/conversations"
OUT_DIR = Path(r"C:\Users\Supritha Kulkarni\inscribe_analysis")

captured = []


def main():
    global captured

    print("Closing any running Edge processes...")
    subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
    time.sleep(2)

    with sync_playwright() as p:
        edge_profile = r"C:\Users\Supritha Kulkarni\AppData\Local\Microsoft\Edge\User Data"
        context = p.chromium.launch_persistent_context(
            user_data_dir=edge_profile,
            channel="msedge",
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()

        # Intercept every JSON response from inscribe.education
        def on_response(response):
            try:
                if "inscribe.education" not in response.url:
                    return
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                data = response.json()
                captured.append({"url": response.url, "data": data})
                print(f"  [API] {response.url[:80]}")
            except Exception:
                pass

        page.on("response", on_response)

        print(f"Opening: {TARGET_URL}")
        page.goto(TARGET_URL)
        page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(3)

        # Scroll to trigger any paginated API calls
        print("Scrolling to load all posts...")
        page.mouse.click(700, 500)
        prev = 0
        for i in range(20):
            page.mouse.wheel(0, 3000)
            time.sleep(2)
            count = len(captured)
            print(f"  Scroll {i+1}: {count} API responses captured")
            if count == prev and i > 3:
                break
            prev = count

        context.close()

    print(f"\nTotal API responses captured: {len(captured)}")

    # Save raw responses for inspection
    raw_path = OUT_DIR / "api_raw.json"
    raw_path.write_text(json.dumps(captured, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Raw responses saved to: {raw_path}")

    # Try to extract conversation records from any response
    records = []
    for entry in captured:
        data = entry["data"]
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ["data", "results", "items", "conversations", "posts",
                        "threads", "content", "records", "collection"]:
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
        if items and isinstance(items[0], dict):
            print(f"  Found {len(items)} items in: {entry['url'][:70]}")
            for item in items:
                item["_source"] = entry["url"]
                records.append(item)

    if not records:
        print("\nNo structured list found in API responses.")
        print(f"Open {raw_path} and share the structure — I'll parse it manually.")
        return

    # Save clean JSON
    json_path = OUT_DIR / "inscribe_conversations.json"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    # Flatten and save CSV
    def flatten(d, prefix=""):
        out = {}
        for k, v in d.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                out.update(flatten(v, f"{key}_"))
            elif isinstance(v, list):
                out[key] = json.dumps(v)
            else:
                out[key] = v
        return out

    flat = [flatten(r) for r in records]
    all_keys = list({k for r in flat for k in r.keys()})
    csv_path = OUT_DIR / "inscribe_conversations.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)

    print(f"\nSaved {len(records)} records to:")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    if records:
        print(f"\nSample keys: {list(records[0].keys())[:10]}")


if __name__ == "__main__":
    main()
