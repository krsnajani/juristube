import json
import subprocess
import datetime
import time
import os
import sys
from db import get_db
from filter_engine import evaluate_video, normalize_title

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

def fetch_channel_videos(channel_url, max_results=30):
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        f"{channel_url.rstrip('/')}/videos"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = proc.stdout.strip().split("\n")
        results = []
        for line in lines[:max_results]:
            if line.strip():
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
        return results
    except Exception as e:
        print(f"Error scraping channel '{channel_url}': {e}")
        return []

def run_channel_ingest(max_channels=None, results_per_channel=25, delay_sec=3):
    channels_file = os.path.join(CONFIG_DIR, "channels.json")
    if not os.path.exists(channels_file):
        print(f"File not found: {channels_file}")
        return

    with open(channels_file, "r") as f:
        channels = json.load(f)

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    total_scanned = 0
    total_added = 0
    channels_processed = 0

    for ch in channels:
        if max_channels and channels_processed >= max_channels:
            break
        channels_processed += 1
        name = ch.get("name")
        url = ch.get("url")
        tier = ch.get("tier", 1)
        subjects = ch.get("subjects", [])
        print(f"[{channels_processed}] Scraping channel: {name} (Tier {tier})...")

        items = fetch_channel_videos(url, max_results=results_per_channel)
        for item in items:
            vid = item.get("id")
            if not vid:
                continue

            total_scanned += 1
            keep, score, content_type, reason = evaluate_video(
                item, source_type="channel", tier=tier
            )
            if not keep:
                continue

            title = item.get("title", "")
            video_url = item.get("url") or f"https://www.youtube.com/watch?v={vid}"
            uploader = item.get("uploader") or item.get("channel") or name
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
                authority_tier = MIN(authority_tier, excluded.authority_tier),
                disciplines = json_insert(coalesce(disciplines, '[]'), '$[#]', ?),
                sources = json_insert(coalesce(sources, '[]'), '$[#]', 'channel'),
                channel_source = coalesce(channel_source, excluded.channel_source),
                updated_at = excluded.updated_at
            """, (
                vid, video_url, title, uploader, desc[:400],
                duration, upload_date, content_type, "evergreen", score,
                tier, json.dumps(["channel"]), json.dumps([]),
                json.dumps([]), name, json.dumps(subjects), json.dumps([]),
                normalize_title(title), now, now, subjects[0] if subjects else "law"
            ))
            total_added += 1

        conn.commit()
        time.sleep(delay_sec)

    conn.close()
    print(f"Channel scrape complete: {total_scanned} scanned, {total_added} accepted/updated.")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_channel_ingest(max_channels=limit)
