import json
import subprocess
import datetime
import time
import os
import sys
from db import get_db
from filter_engine import evaluate_video, normalize_title

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

def fetch_search_results(query, max_results=10):
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        f"ytsearch{max_results}:{query}"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = proc.stdout.strip().split("\n")
        results = []
        for line in lines:
            if line.strip():
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
        return results
    except Exception as e:
        print(f"Error querying yt-dlp for '{query}': {e}")
        return []

def run_scholar_search(max_scholars=None, results_per_scholar=10, delay_sec=2):
    scholars_file = os.path.join(CONFIG_DIR, "scholars.json")
    if not os.path.exists(scholars_file):
        print(f"File not found: {scholars_file}")
        return

    with open(scholars_file, "r") as f:
        scholars_by_discipline = json.load(f)

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    total_scanned = 0
    total_added = 0
    scholars_processed = 0

    for discipline, scholars in scholars_by_discipline.items():
        for scholar in scholars:
            if max_scholars and scholars_processed >= max_scholars:
                break
            scholars_processed += 1
            print(f"[{scholars_processed}] Searching for: {scholar} ({discipline})...")
            
            # Query combining academic qualifiers
            query = f'"{scholar}" lecture OR talk OR keynote OR address OR symposium OR "book discussion"'
            items = fetch_search_results(query, max_results=results_per_scholar)

            for item in items:
                vid = item.get("id")
                if not vid:
                    continue

                total_scanned += 1
                keep, score, content_type, reason = evaluate_video(
                    item, scholar_name=scholar, source_type="scholar_search", tier=3
                )
                if not keep:
                    continue

                title = item.get("title", "")
                url = item.get("url") or f"https://www.youtube.com/watch?v={vid}"
                channel = item.get("uploader") or item.get("channel", "")
                duration = item.get("duration") or 0
                upload_date = item.get("upload_date")

                desc = item.get("description") or ""
                cursor.execute("""
                INSERT INTO videos (
                    vid, url, title, channel, summary, duration_sec, upload_date,
                    content_type, shelf_life, score, authority_tier, sources,
                    scholar_matches, blog_sources, channel_source, disciplines,
                    tags, title_normalized, discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vid) DO UPDATE SET
                    score = MAX(score, excluded.score),
                    scholar_matches = json_insert(coalesce(scholar_matches, '[]'), '$[#]', ?),
                    disciplines = json_insert(coalesce(disciplines, '[]'), '$[#]', ?),
                    sources = json_insert(coalesce(sources, '[]'), '$[#]', 'scholar_search'),
                    updated_at = excluded.updated_at
                """, (
                    vid, url, title, channel, desc[:400],
                    duration, upload_date, content_type, "evergreen", score,
                    3, json.dumps(["scholar_search"]), json.dumps([scholar]),
                    json.dumps([]), None, json.dumps([discipline]), json.dumps([]),
                    normalize_title(title), now, now, scholar, discipline
                ))
                total_added += 1

            conn.commit()
            time.sleep(delay_sec)

        if max_scholars and scholars_processed >= max_scholars:
            break

    conn.close()
    print(f"Scholar search complete: {total_scanned} scanned, {total_added} accepted/updated.")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_scholar_search(max_scholars=limit)
