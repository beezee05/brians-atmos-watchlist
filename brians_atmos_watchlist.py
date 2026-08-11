import feedparser
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

SOURCE_FEED = "https://spatialaudiodb.com/rss/dolby-atmos.xml"
OUTPUT_FILE = "brians_atmos_watchlist.xml"

FEED_TITLE = "Brian's Atmos Watchlist"
FEED_DESCRIPTION = (
    "New Dolby Atmos and Spatial Audio releases, remasters and upgrades "
    "filtered for rock and related genres."
)
FEED_LINK = "https://spatialaudiodb.com/"

# Genres we want.
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
    "singer-songwriter",
]

# Things we definitely don't want.
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
    " ost",
    "anime soundtrack",
    "character song",
    "character album",
    "children",
    "children's",
    "kids music",
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
    "dj mix",
    "dj set",
    "edc ",
    "house music",
    "deep house",
    "tech house",
    "techno",
    "trance",
    "dubstep",
    "drum and bass",
    "drum & bass",
    "electronic dance",
    "dance music",
    "edm",
    "electro house",
    "future bass",
    "hardstyle",
    "reggaeton",
    "latin urban",
    "dancehall",
]

# Strong indicators of an important catalog release.
LEGACY_TERMS = [
    "remaster",
    "remastered",
    "anniversary edition",
    "deluxe edition",
    "expanded edition",
    "super deluxe",
    "box set",
    "atmos mix",
    "dolby atmos",
    "spatial audio",
]

# Artists whose catalog is overwhelmingly relevant to this feed.
# This is a BOOST/SAFETY NET, not a whitelist.
LEGACY_ARTISTS = [
    "pink floyd",
    "the beatles",
    "rolling stones",
    "led zeppelin",
    "genesis",
    "phil collins",
    "peter gabriel",
    "dire straits",
    "mark knopfler",
    "fleetwood mac",
    "eagles",
    "steely dan",
    "supertramp",
    "the police",
    "sting",
    "the doors",
    "david bowie",
    "bruce springsteen",
    "tom petty",
    "billy joel",
    "elton john",
    "rush",
    "yes",
    "jethro tull",
    "toto",
    "chicago",
    "electric light orchestra",
    "elo",
    "tears for fears",
    "talk talk",
    "simple minds",
    "roxy music",
    "joe jackson",
    "genesis",
    "u2",
    "queen",
    "ac/dc",
    "van halen",
    "def leppard",
    "bon jovi",
    "journey",
    "boston",
    "foreigner",
    "styx",
    "heart",
    "pat benatar",
    "bryan adams",
    "hall & oates",
    "huey lewis",
    "red hot chili peppers",
    "r.e.m.",
    "the cure",
    "depeche mode",
    "new order",
    "the fixx",
    "alan parsons",
    "alan parsons project",
    "supertramp",
    "marvin gaye",
    "bob dylan",
    "neil young",
    "joni mitchell",
    "van morrison",
    "eric clapton",
    "jeff beck",
    "steely dan",
]


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_entry_text(entry):
    parts = []

    for field in [
        "title",
        "summary",
        "description",
        "author",
    ]:
        value = entry.get(field)

        if value:
            parts.append(str(value))

    for tag in entry.get("tags", []):
        if isinstance(tag, dict):
            parts.append(str(tag.get("term", "")))

    return clean_text(" ".join(parts))


def contains_negative_term(text):
    lower = text.lower()

    for term in NEGATIVE_TERMS:
        if term in lower:
            return True

    return False


def has_positive_genre(text):
    lower = text.lower()

    for genre in POSITIVE_GENRES:
        if genre in lower:
            return True

    return False


def is_legacy_artist(text):
    lower = text.lower()

    for artist in LEGACY_ARTISTS:
        if artist in lower:
            return True

    return False


def has_legacy_term(text):
    lower = text.lower()

    for term in LEGACY_TERMS:
        if term in lower:
            return True

    return False


def should_keep(entry):
    text = get_entry_text(entry)
    lower = text.lower()

    # First and most important rule:
    # obvious unwanted material is ALWAYS rejected.
    if contains_negative_term(text):
        return False

    # Explicit rock-related genre = keep.
    if has_positive_genre(text):
        return True

    # Established legacy rock artist + important catalog release = keep.
    if is_legacy_artist(text) and has_legacy_term(text):
        return True

    # Do NOT allow generic remixes, Atmos releases or electronic material
    # through without a rock-related genre or legacy artist.
    return False


def parse_date(entry):
    raw = entry.get("published") or entry.get("updated")

    if raw:
        try:
            dt = parsedate_to_datetime(raw)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)
        except Exception:
            pass

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


def get_artist(entry):
    author = clean_text(entry.get("author", ""))

    if author:
        return author

    title = clean_text(entry.get("title", ""))

    # Many Spatial Audio Database entries use:
    # "Album Title - Artist"
    if " - " in title:
        pieces = title.rsplit(" - ", 1)

        if len(pieces) == 2:
            return pieces[1].strip()

    return ""


def get_release_type(entry):
    title = clean_text(entry.get("title", "")).lower()

    if "album" in title:
        return "Album"

    if "ep" in title:
        return "EP"

    if "single" in title:
        return "Single"

    return "Release"


def make_description(entry):
    text = get_entry_text(entry)

    labels = []

    if "dolby atmos" in text.lower():
        labels.append("Dolby Atmos")

    if "spatial audio" in text.lower():
        labels.append("Spatial Audio")

    if "remaster" in text.lower():
        labels.append("Remaster")

    if "anniversary" in text.lower():
        labels.append("Anniversary Edition")

    if "deluxe" in text.lower():
        labels.append("Deluxe Edition")

    if not labels:
        labels.append("Dolby Atmos release")

    return " • ".join(dict.fromkeys(labels))


def make_rss_item(channel, entry):
    item = SubElement(channel, "item")

    title = clean_text(entry.get("title", "Untitled release"))
    link = entry.get("link", "")

    artist = get_artist(entry)
    release_type = get_release_type(entry)
    description = make_description(entry)

    # Make the title a little cleaner when artist information is available.
    if artist and artist.lower() not in title.lower():
        display_title = f"{artist} — {title}"
    else:
        display_title = title

    SubElement(item, "title").text = display_title

    if link:
        SubElement(item, "link").text = link

    guid = SubElement(item, "guid")
    guid.set("isPermaLink", "false")
    guid.text = link or display_title

    if artist:
        description = f"{release_type} • {description} • {artist}"
    else:
        description = f"{release_type} • {description}"

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

    kept.sort(
        key=parse_date,
        reverse=True
    )

    print(f"Filtered entries: {len(kept)}")

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

    # Keep the feed manageable.
    for entry in kept[:50]:
        make_rss_item(channel, entry)

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
