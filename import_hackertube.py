import json
import sqlite3
import re
import datetime
import os
from db import get_db

HACKERTUBE_DIR = "/tmp/hackertube-data"
VIDEOS_FILE = os.path.join(HACKERTUBE_DIR, "videos.jsonl")

DISCIPLINE_MAP = {
    "philosophy-ethics": "political-philosophy",
    "religion-belief": "social-theory",
    "language-linguistics": "social-theory",
    "university-lectures": "university-lectures",
    "us-politics": "constitutional-law",
    "law-policing-justice": "constitutional-law",
    "free-speech-censorship": "constitutional-law",
    "world-history": "history-intellectual",
    "military-warfare": "history-intellectual",
    "social-issues-culture": "social-theory",
    "macroeconomics": "economics-political-economy",
    "microeconomics-behavioral": "economics-political-economy",
    "labor-work-wealth": "economics-political-economy",
    "history-of-computing": "history-intellectual",
    "hacker-culture-free-software": "media-technology-law",
    "ai-safety-impact": "media-technology-law"
}

def normalize_title(title):
    return re.sub(r'[^a-z0-9]', '', title.lower())

def import_hackertube():
    if not os.path.exists(VIDEOS_FILE):
        print(f"Error: {VIDEOS_FILE} does not exist. Please extract hackertube data first.")
        return

    conn = get_db()
    cursor = conn.cursor()

    count = 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with open(VIDEOS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            vid = item.get("vid")
            if not vid:
                continue

            categories = item.get("categories", [])
            matched_disciplines = set()
            for cat in categories:
                cat_id = cat.get("id")
                if cat_id in DISCIPLINE_MAP:
                    matched_disciplines.add(DISCIPLINE_MAP[cat_id])

            ht_score = float(item.get("score", 0.0))
            score = ht_score
            if matched_disciplines:
                score += 3.0  # Boost humanities/law relevance

            title = item.get("title", "")
            title_norm = normalize_title(title)

            cursor.execute("""
            INSERT INTO videos (
                vid, url, title, channel, summary, duration_sec, upload_date,
                content_type, shelf_life, score, ht_score, authority_tier,
                sources, scholar_matches, blog_sources, channel_source,
                disciplines, tags, ht_categories, title_normalized, discovered_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vid) DO UPDATE SET
                score = MAX(score, excluded.score),
                ht_score = excluded.ht_score,
                sources = json_insert(coalesce(sources, '[]'), '$[#]', 'hackertube'),
                updated_at = excluded.updated_at
            """, (
                vid,
                item.get("url", f"https://www.youtube.com/watch?v={vid}"),
                title,
                item.get("channel", ""),
                item.get("summary", ""),
                0,
                None,
                item.get("content_type", "talk"),
                item.get("shelf_life", "evergreen"),
                score,
                ht_score,
                2 if matched_disciplines else 3,
                json.dumps(["hackertube"]),
                json.dumps([]),
                json.dumps([]),
                None,
                json.dumps(list(matched_disciplines)),
                json.dumps(item.get("tags", [])),
                json.dumps(categories),
                title_norm,
                now,
                now
            ))
            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} HackerTube videos into database.")

if __name__ == "__main__":
    import_hackertube()
