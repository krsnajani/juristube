import json
import urllib.request
import xml.etree.ElementTree as ET
import re
import datetime
import subprocess
import os
import sys
from db import get_db
from filter_engine import evaluate_video, normalize_title

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

YT_URL_REGEX = re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})')

def fetch_feed_xml(url):
    headers = {"User-Agent": "Mozilla/5.0 (JurisTube Academic Harvester)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"Error fetching feed {url}: {e}")
        return None

def fetch_video_meta(vid):
    cmd = ["yt-dlp", "--dump-json", f"https://www.youtube.com/watch?v={vid}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)
    except Exception as e:
        print(f"Error fetching video {vid} with yt-dlp: {e}")
        return None

def run_blog_ingest():
    feeds_file = os.path.join(CONFIG_DIR, "feeds.json")
    if not os.path.exists(feeds_file):
        print(f"File not found: {feeds_file}")
        return

    with open(feeds_file, "r") as f:
        feeds = json.load(f)

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    total_links_found = 0
    total_added = 0

    for feed in feeds:
        name = feed.get("name")
        url = feed.get("url")
        subjects = feed.get("subjects", [])
        print(f"Mining blog feed: {name}...")

        raw_xml = fetch_feed_xml(url)
        if not raw_xml:
            continue

        try:
            root = ET.fromstring(raw_xml)
        except Exception as e:
            print(f"Error parsing XML from {name}: {e}")
            continue

        # Look in all text fields
        text_content = []
        for elem in root.iter():
            if elem.text:
                text_content.append(elem.text)

        full_blob = " ".join(text_content)
        vids = set(YT_URL_REGEX.findall(full_blob))
        print(f"  Found {len(vids)} YouTube links in {name}.")

        for vid in vids:
            total_links_found += 1
            # Check if video already exists
            cursor.execute("SELECT vid FROM videos WHERE vid = ?", (vid,))
            existing = cursor.fetchone()

            if existing:
                # Update with blog source
                cursor.execute("""
                UPDATE videos SET
                    blog_sources = json_insert(coalesce(blog_sources, '[]'), '$[#]', ?),
                    sources = json_insert(coalesce(sources, '[]'), '$[#]', 'blog'),
                    score = score + 4.0,
                    updated_at = ?
                WHERE vid = ?
                """, (name, now, vid))
                total_added += 1
            else:
                # Fetch metadata via yt-dlp
                meta = fetch_video_meta(vid)
                if not meta:
                    continue

                keep, score, content_type, reason = evaluate_video(
                    meta, source_type="blog", tier=1
                )
                if not keep:
                    continue

                title = meta.get("title", "")
                video_url = f"https://www.youtube.com/watch?v={vid}"
                channel = meta.get("uploader") or meta.get("channel", "")
                duration = meta.get("duration") or 0
                upload_date = meta.get("upload_date")
                desc = meta.get("description") or ""

                cursor.execute("""
                INSERT INTO videos (
                    vid, url, title, channel, summary, duration_sec, upload_date,
                    content_type, shelf_life, score, authority_tier, sources,
                    scholar_matches, blog_sources, channel_source, disciplines,
                    tags, title_normalized, discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid, video_url, title, channel, desc[:400],
                    duration, upload_date, content_type, "evergreen", score,
                    1, json.dumps(["blog"]), json.dumps([]),
                    json.dumps([name]), None, json.dumps(subjects), json.dumps([]),
                    normalize_title(title), now, now
                ))
                total_added += 1

        conn.commit()

    conn.close()
    print(f"Blog mining complete: {total_links_found} links found, {total_added} added/updated.")

if __name__ == "__main__":
    run_blog_ingest()
