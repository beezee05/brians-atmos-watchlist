import feedparser
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring

SOURCE_FEED = "https://spatialaudiodb.com/rss/dolby-atmos.xml"
OUTPUT_FILE = "brians_atmos_watchlist.xml"

FEED_TITLE = "Brian's Atmos Watchlist"
FEED_DESCRIPTION = (
    "Filtered Dolby Atmos releases, remasters and upgrades "
    "focused on rock and related genres."
)
FEED_LINK = "https://spatialaudiodb.com/"

# Genres/styles we WANT.
POSITIVE_GENRES = [
    "rock",
    "classic rock",
    "alternative rock",
    "hard rock",
    "progressive rock",
    "prog rock",
    "indie rock",
    "blues rock",
    "southern rock",
    "folk rock",
    "garage rock",
    "psychedelic rock",
    "punk rock",
    "pop punk",
    "post-punk",
    "new wave",
    "grunge",
    "metal",
    "heavy metal",
    "hardcore",
    "industrial rock",
    "gothic rock",
    "art rock",
    "soft rock",
    "country rock",
    "americana",
    "blues",
    "singer-songwriter",
    "alternative",
    "indie",
    "pop",
]

# Things we definitely DON'T want.
NEGATIVE_TERMS = [
    "anime",
    "j-pop",
    "jpop",
    "k-pop",
    "kpop",
    "idol",
    "vocaloid",
    "manga",
    "visual novel",
    "video game",
    "video games",
    "game soundtrack",
    "game music",
    "soundtrack",
    "original soundtrack",
    "ost",
    "anime soundtrack",
    "character song",
    "character album",
    "children",
    "children's",
    "kids",
    "nursery",
    "meditation",
    "sleep music",
    "relaxation",
    "yoga",
    "christmas",
    "holiday music",
    "worship",
    "gospel",
    "classical",
    "opera",
    "jazz",
    "easy listening",
    "spoken word",
    "audiobook",
    "comedy",
    "podcast",
    "karaoke",
    "tribute band",
    "tribute album",
]

# These are strong indicators that the item is a legacy/remaster/remix
# or an important Atmos upgrade.
SPECIAL_TERMS = [
    "remaster",
    "remastered",
    "remix",
    "2026 mix",
    "2025 mix",
    "2024 mix",
    "anniversary",
    "deluxe edition",
    "expanded edition",
    "atmos mix",
    "dolby atmos",
    "spatial audio",
    "immersive",
]


def clean_text(value):
    """Strip HTML and normalize whitespace."""
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_entry_text(entry):
    """Combine the useful RSS fields into searchable text."""
    parts = []

    for field in [
        "title",
        "summary",
        "description",
        "author",
        "category",
        "tags",
    ]:
        value = entry.get(field)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    parts.append(str(item.get("term", "")))
                else:
                    parts.append(str(item))
        elif isinstance(value, dict):
            parts.append(str(value.get("term", "")))
        elif value:
            parts.append(str(value))

    # Also inspect any RSS category tags feedparser exposes.
    for tag in entry.get("tags", []):
        if isinstance(tag, dict):
            parts.append(str(tag.get("term", "")))

    return clean_text(" ".join(parts))


def contains_negative_term(text):
    text_lower = text.lower()

    for term in NEGATIVE_TERMS:
        if term in text_lower:
            return True

    return False


def has_positive_genre(text):
    text_lower = text.lower()

    for genre in POSITIVE_GENRES:
        if genre in text_lower:
            return True

    return False


def has_special_term(text):
    text_lower = text.lower()

    for term in SPECIAL_TERMS:
        if term in text_lower:
            return True

    return False


def should_keep(entry):
    """
    Keep music that looks relevant to Brian's preferred genres.

    We use a conservative filter:
    - Explicit unwanted genres/content are rejected.
    - Explicit rock/related genres are accepted.
    - Important remasters/remixes/Atmos upgrades can pass when they
      aren't clearly from an unwanted category.
    """

    text = get_entry_text(entry)
    lower = text.lower()

    # First, remove obvious noise.
    if contains_negative_term(text):
        return False

    # Explicitly relevant genres get through.
    if has_positive_genre(text):
        return True

    # Legacy/remaster/Atmos releases get a secondary chance,
    # but only if they don't contain obvious unwanted content.
    if has_special_term(text):
        # Avoid letting generic pop/unknown releases flood the feed.
        # Require a recognizable musical context.
        music_context = [
            "album",
            "single",
            "ep",
            "release",
            "artist",
            "band",
            "rock",
            "music",
        ]

        return any(term in lower for term in music_context)

    return False


def parse_date(entry):
    """Return a timezone-aware datetime."""
    raw = entry.get("published") or entry.get("updated")

    if raw:
        try:
            dt = parsedate_to_datetime(raw)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    # Feedparser often provides a parsed time tuple.
    for field in ["published_parsed", "updated_parsed"]:
        value = entry.get(field)

        if value:
            try:
                return datetime(
                    *value[:6],
                    tzinfo=timezone.utc
                )
            except Exception:
                pass

    return datetime.now(timezone.utc)


def make_rss_item(channel, entry):
    item = SubElement(channel, "item")

    title = clean_text(entry.get("title", "Untitled release"))
    link = entry.get("link", "")
    description = clean_text(
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    # Keep descriptions reasonably short.
    if len(description) > 1000:
        description = description[:997] + "..."

    SubElement(item, "title").text = title

    if link:
        SubElement(item, "link").text = link

    guid = SubElement(item, "guid")
    guid.set("isPermaLink", "false")
    guid.text = link or title

    SubElement(item, "description").text = description

    pub_date = parse_date(entry)
    SubElement(item, "pubDate").text = pub_date.strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    return item


def main():
    print("Downloading Spatial Audio Database feed...")
    feed = feedparser.parse(SOURCE_FEED)

    if feed.bozo and not feed.entries:
        raise RuntimeError(
            "Could not read the Spatial Audio Database RSS feed."
        )

    print(f"Source entries: {len(feed.entries)}")

    kept = []

    for entry in feed.entries:
        if should_keep(entry):
            kept.append(entry)

    # Newest first.
    kept.sort(
        key=parse_date,
        reverse=True
    )

    print(f"Filtered entries: {len(kept)}")

    # Build RSS 2.0.
    rss = Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = FEED_TITLE
    SubElement(channel, "link").text = FEED_LINK
    SubElement(channel, "description").text = FEED_DESCRIPTION
    SubElement(channel, "language").text = "en-ca"

    # Prevent an unexpectedly huge feed.
    for entry in kept[:50]:
        make_rss_item(channel, entry)

    # Write UTF-8 RSS XML.
    tree = ElementTree(rss)
    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"Created {OUTPUT_FILE}")
    print(f"Items in feed: {min(len(kept), 50)}")


if __name__ == "__main__":
    main()
