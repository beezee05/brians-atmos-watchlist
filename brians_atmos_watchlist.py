import feedparser
from feedgen.feed import FeedGenerator
import re
from datetime import datetime

SOURCE_FEED = "https://spatialaudiodb.com/rss/dolby-atmos.xml"
OUTPUT_FILE = "brians_atmos_watchlist.xml"

INCLUDE_GENRES = [
    "rock", "classic rock", "progressive rock", "prog rock",
    "alternative rock", "blues rock", "folk rock", "pop rock",
    "new wave", "power pop", "singer-songwriter", "jazz fusion"
]

INCLUDE_KEYWORDS = [
    "dolby atmos", "spatial audio", "apple digital masters",
    "remaster", "remastered", "deluxe edition",
    "anniversary edition", "expanded edition", "super deluxe"
]

EXCLUDE_KEYWORDS = [
    "hip-hop", "hip hop", "rap", "k-pop", "j-pop",
    "edm", "house", "techno", "trance", "reggaeton",
    "latin urban", "podcast", "karaoke", "meditation",
    "sleep", "white noise", "children", "sound effects"
]

def text(entry):
    parts = [
        entry.get("title", ""),
        entry.get("summary", ""),
        " ".join(tag.get("term", "") for tag in entry.get("tags", []))
    ]
    return " ".join(parts).lower()

def is_album(title):
    t = title.lower()
    return not any(x in t for x in [" single", " ep", " - single", " - ep"])

def include_entry(entry):
    t = text(entry)

    if any(word in t for word in EXCLUDE_KEYWORDS):
        return False

    genre_match = any(g in t for g in INCLUDE_GENRES)
    keyword_match = any(k in t for k in INCLUDE_KEYWORDS)

    return genre_match or keyword_match

feed = feedparser.parse(SOURCE_FEED)

fg = FeedGenerator()
fg.title("Brian's Atmos Watchlist")
fg.link(href="https://spatialaudiodb.com")
fg.description("Filtered Dolby Atmos, Apple Digital Masters, and remaster releases focused on rock, prog, blues, and classic pop.")
fg.language("en")

seen_albums = set()

for entry in feed.entries:
    title = entry.get("title", "Untitled")

    if not include_entry(entry):
        continue

    if not is_album(title):
        continue

    album_key = re.sub(r"\s*\(.*?\)\s*", "", title.lower()).strip()

    if album_key in seen_albums:
        continue

    seen_albums.add(album_key)

    fe = fg.add_entry()
    fe.title(title)
    fe.link(href=entry.get("link", "https://spatialaudiodb.com"))
    fe.description(entry.get("summary", ""))

    published = entry.get("published_parsed")
    if published:
        fe.pubDate(datetime(*published[:6]))

fg.rss_file(OUTPUT_FILE)

print(f"Created {OUTPUT_FILE} with {len(seen_albums)} filtered album entries.")

