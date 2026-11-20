import re

SLOP_PATTERNS = [
    r'\b(DESTROYS|SLAMS|OWNS|OBLITERATES|WRECKS|HUMILIATES)\b',
    r'\b(SHOCKING|INSANE|UNBELIEVABLE|YOU WON\'T BELIEVE)\b',
    r'\breaction\b',
    r'\bshorts?\b',
    r'\bcompilation\b',
    r'\btop\s+\d+\b',
    r'\b(podcast\s+)?ep(isode)?\s*#?\d+\b',
    r'\btrailer\b',
    r'\bpromo\b',
    r'\btiktok\b',
    r'\b(full\s+)?movie\b',
    r'#shorts',
]

ACADEMIC_BOOST_PATTERNS = [
    r'\blecture\b',
    r'\bkeynote\b',
    r'\b(memorial|inaugural|endowed)\s+lecture\b',
    r'\bsymposium\b',
    r'\bcolloquium\b',
    r'\bseminar\b',
    r'\bworkshop\b',
    r'\bbook\s+(launch|discussion|talk|event)\b',
    r'\btanner\s+lectures?\b',
    r'\bhamlyn\s+lectures?\b',
    r'\b(chair|introduction|introduced)\s+by\b',
    r'\boral\s+argument\b',
    r'\bpanel\s+discussion\b',
    r'\bfaculty\b',
    r'\bjurisprudence\b',
    r'\bconstitutional\b',
]

def normalize_title(title):
    return re.sub(r'[^a-z0-9]', '', (title or "").lower())

def is_slop(title):
    for pattern in SLOP_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False

def evaluate_video(item, scholar_name=None, source_type="scholar_search", tier=3):
    """
    Returns (keep: bool, score: float, content_type: str, reason: str)
    """
    title = item.get("title", "")
    duration = item.get("duration") or 0

    # 1. Duration check (only if duration is known)
    # 20 min = 1200 sec, 35 min = 2100 sec
    content_type = "talk"
    if duration > 0 and duration < 1200:
        return False, 0.0, "", "Duration < 20 min"
    elif duration >= 1200 and duration < 2100:
        content_type = "short_talk"
    elif duration >= 10800: # 3 hrs
        content_type = "marathon"
    elif duration >= 2100:
        content_type = "lecture"

    # 2. Slop filter
    if is_slop(title):
        return False, 0.0, "", "Title matched slop pattern"

    # 3. Base scoring
    score = 5.0
    if duration >= 2100:
        score += 3.0
    elif duration >= 3600:
        score += 5.0

    # Academic title bonus
    for pattern in ACADEMIC_BOOST_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            score += 2.5
            break

    # Authority tier
    if tier == 1:
        score *= 1.5
    elif tier == 2:
        score *= 1.2

    # Scholar match
    if scholar_name and scholar_name.lower() in title.lower():
        score += 3.0

    if source_type == "blog":
        score += 4.0
    elif source_type == "channel":
        score += 2.0

    return True, score, content_type, "Accepted"
