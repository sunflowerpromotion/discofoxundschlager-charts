import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


# ============================================================
# KONFIGURATION
# ============================================================

STATION = "discofoxundschlager"

API_URL = (
    f"https://api.laut.fm/station/{STATION}/last_songs"
)

MAX_CHARTS = 20

TIMEZONE = ZoneInfo("Europe/Berlin")

DATA_DIR = Path("data")

STATS_FILE = DATA_DIR / "stats.json"
CHARTS_FILE = DATA_DIR / "charts.json"


# ============================================================
# AUSGESCHLOSSENE EINTRÄGE
# ============================================================

# Begriffe, die nicht in die Musikcharts sollen.
#
# Die Prüfung erfolgt auf Artist + Titel.
#
# Du kannst später weitere Begriffe ergänzen.

EXCLUDED_TERMS = [

    "station id",
    "station-id",
    "stationid",

    "jingle",
    "jingles",

    "promo",
    "promos",

    "werbung",
    "werbespot",

    "commercial",

    "news",
    "nachrichten",

    "moderation",

    "aircheck",

    "voiceover",
    "voice over",

    "sponsor",

    "ident",

    "sweeper",

    "liner"

]


# ============================================================
# VERZEICHNIS
# ============================================================

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# JSON LADEN
# ============================================================

def load_json(path, default):

    if not path.exists():

        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"Warnung beim Laden von {path}:"
        )

        print(error)

        return default


# ============================================================
# JSON SPEICHERN
# ============================================================

def save_json(path, data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# AKTUELLE WOCHE
# ============================================================

def get_current_week():

    now = datetime.now(
        TIMEZONE
    )

    return now.strftime(
        "%G-W%V"
    )


# ============================================================
# DATUM PARSEN
# ============================================================

def parse_date(value):

    if not value:

        return None

    value = str(
        value
    ).strip()

    try:

        if value.endswith("Z"):

            value = (
                value[:-1]
                + "+00:00"
            )

        date = datetime.fromisoformat(
            value
        )

        if date.tzinfo is None:

            date = date.replace(
                tzinfo=TIMEZONE
            )

        return date.astimezone(
            TIMEZONE
        )

    except Exception:

        return None


# ============================================================
# KÜNSTLERNAME
# ============================================================

def get_artist(song):

    artist_data = song.get(
        "artist",
        {}
    )

    if isinstance(
        artist_data,
        dict
    ):

        artist = artist_data.get(
            "name",
            ""
        )

    else:

        artist = str(
            artist_data
        )


    artist = (
        artist
        or "Unbekannter Künstler"
    ).strip()


    return artist


# ============================================================
# TITEL
# ============================================================

def get_title(song):

    title = song.get(
        "title",
        ""
    )


    title = (
        title
        or "Unbekannter Titel"
    ).strip()


    return title


# ============================================================
# PRÜFEN, OB ES EIN NICHT-MUSIK-EINTRAG IST
# ============================================================

def is_excluded(song):

    artist = get_artist(
        song
    )

    title = get_title(
        song
    )


    search_text = (
        artist
        + " "
        + title
    ).lower()


    for term in EXCLUDED_TERMS:

        if term in search_text:

            return True


    return False


# ============================================================
# SONG-ID
# ============================================================

def song_id(song):

    artist = get_artist(
        song
    )

    title = get_title(
        song
    )


    return (
        artist.lower()
        + "|||"
        + title.lower()
    )


# ============================================================
# PLAY-ID
# ============================================================

def play_id(song):

    started_at = str(
        song.get(
            "started_at",
            ""
        )
    ).strip()


    return (
        song_id(song)
        + "|||"
        + started_at
    )


# ============================================================
# LAUT.FM API
# ============================================================

print("")
print(
    "=========================================="
)
print(
    "Discofox & Schlager Charts"
)
print(
    "laut.fm Daten werden geladen..."
)
print(
    "=========================================="
)
print("")


request = urllib.request.Request(

    API_URL,

    headers={

        "User-Agent":
            "Discofoxundschlager-Charts/2.0"
    }
)


try:

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

except Exception as error:

    print(
        "FEHLER: laut.fm API konnte "
        "nicht abgerufen werden."
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# API-ANTWORT PRÜFEN
# ============================================================

if not isinstance(
    data,
    list
):

    print(
        "FEHLER: API-Antwort ist "
        "keine Liste."
    )

    raise SystemExit(1)


print(
    f"API liefert {len(data)} Einträge."
)

print("")


# ============================================================
# STATISTIK LADEN
# ============================================================

stats = load_json(

    STATS_FILE,

    {

        "current_week":
            get_current_week(),

        "weeks":
            {},

        "processed_plays":
            []

    }

)


# ============================================================
# DATENSTRUKTUR PRÜFEN
# ============================================================

if not isinstance(
    stats,
    dict
):

    stats = {

        "current_week":
            get_current_week(),

        "weeks":
            {},

        "processed_plays":
            []

    }


if "weeks" not in stats:

    stats["weeks"] = {}


if "processed_plays" not in stats:

    stats["processed_plays"] = []


# ============================================================
# AKTUELLE WOCHE
# ============================================================

current_week = get_current_week()


old_week = stats.get(
    "current_week"
)


if old_week != current_week:

    print(
        f"Wöchentlicher Wechsel: "
        f"{old_week} -> {current_week}"
    )

    stats["current_week"] = current_week


# ============================================================
# AKTUELLE WOCHE ANLEGEN
# ============================================================

if current_week not in stats["weeks"]:

    stats["weeks"][current_week] = {}


# ============================================================
# VERARBEITETE PLAYS
# ============================================================

processed = set(
    stats.get(
        "processed_plays",
        []
    )
)


new_plays = 0

ignored_entries = 0

old_entries = 0


# ============================================================
# SONGS DURCHLAUFEN
# ============================================================

for song in data:

    if not isinstance(
        song,
        dict
    ):

        continue


    # --------------------------------------------------------
    # NICHT-MUSIK EINTRÄGE FILTERN
    # --------------------------------------------------------

    if is_excluded(song):

        ignored_entries += 1

        print(
            "Übersprungen:",
            get_artist(song),
            "-",
            get_title(song)
        )

        continue


    # --------------------------------------------------------
    # STARTZEIT
    # --------------------------------------------------------

    started_at = song.get(
        "started_at"
    )


    if not started_at:

        continue


    parsed_date = parse_date(
        started_at
    )


    if parsed_date is None:

        continue


    # --------------------------------------------------------
    # PLAY-ID
    # --------------------------------------------------------

    current_play_id = play_id(
        song
    )


    # Bereits verarbeitet?

    if current_play_id in processed:

        old_entries += 1

        continue


    # --------------------------------------------------------
    # PLAY SPEICHERN
    # --------------------------------------------------------

    processed.add(
        current_play_id
    )


    artist = get_artist(
        song
    )

    title = get_title(
        song
    )


    # --------------------------------------------------------
    # WOCHE DES PLAYS
    # --------------------------------------------------------

    play_week = parsed_date.strftime(
        "%G-W%V"
    )


    if play_week not in stats["weeks"]:

        stats["weeks"][play_week] = {}


    week = stats[
        "weeks"
    ][play_week]


    # --------------------------------------------------------
    # SONG IDENTIFIZIEREN
    # --------------------------------------------------------

    identifier = song_id(
        song
    )


    # --------------------------------------------------------
    # SONG ANLEGEN
    # --------------------------------------------------------

    if identifier not in week:

        week[identifier] = {

            "artist":
                artist,

            "title":
                title,

            "plays":
                0

        }


    # --------------------------------------------------------
    # PLAY ZÄHLEN
    # --------------------------------------------------------

    week[
        identifier
    ]["plays"] += 1


    new_plays += 1


# ============================================================
# PLAY-HISTORIE BEGRENZEN
# ============================================================

processed_list = list(
    processed
)


if len(processed_list) > 10000:

    processed_list = (
        processed_list[-10000:]
    )


stats["processed_plays"] = (
    processed_list
)


# ============================================================
# ALTE WOCHEN LÖSCHEN
# ============================================================

all_weeks = sorted(

    stats["weeks"].keys(),

    reverse=True
)


for old_week_name in all_weeks[8:]:

    del stats[
        "weeks"
    ][old_week_name]


# ============================================================
# AKTUELLE CHARTS ERSTELLEN
# ============================================================

current_week_data = stats[
    "weeks"
].get(
    current_week,
    {}
)


chart_items = []


for identifier, song in current_week_data.items():

    chart_items.append({

        "artist":
            song["artist"],

        "title":
            song["title"],

        "plays":
            song["plays"]

    })


# ============================================================
# NACH PLAYS SORTIEREN
# ============================================================

chart_items.sort(

    key=lambda item: (

        -item["plays"],

        item["artist"].lower(),

        item["title"].lower()

    )

)


# ============================================================
# TOP 20
# ============================================================

chart_items = chart_items[
    :MAX_CHARTS
]


# ============================================================
# VORWOCHE ERMITTELN
# ============================================================

sorted_weeks = sorted(

    stats["weeks"].keys(),

    reverse=True
)


previous_week = None


for week_name in sorted_weeks:

    if week_name < current_week:

        previous_week = week_name

        break


# ============================================================
# VORWOCHE-CHARTS LADEN
# ============================================================

previous_week_data = {}


if previous_week:

    previous_week_data = stats[
        "weeks"
    ].get(
        previous_week,
        {}
    )


previous_positions = {}


previous_sorted = []


for identifier, song in previous_week_data.items():

    previous_sorted.append({

        "identifier":
            identifier,

        "plays":
            song["plays"]

    })


previous_sorted.sort(

    key=lambda item:
        -item["plays"]

)


for position, item in enumerate(

    previous_sorted,

    start=1

):

    previous_positions[
        item["identifier"]
    ] = position


# ============================================================
# CHARTS MIT POSITION UND TREND
# ============================================================

charts = []


for position, song in enumerate(

    chart_items,

    start=1

):

    identifier = song_id({

        "artist": {
            "name":
                song["artist"]
        },

        "title":
            song["title"]

    })


    old_position = previous_positions.get(
        identifier
    )


    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    if old_position is None:

        trend = "new"

        movement = None


    else:

        movement = (
            old_position
            - position
        )


        if movement > 0:

            trend = "up"

        elif movement < 0:

            trend = "down"

        else:

            trend = "same"


    charts.append({

        "position":
            position,

        "artist":
            song["artist"],

        "title":
            song["title"],

        "plays":
            song["plays"],

        "previous_position":
            old_position,

        "movement":
            movement,

        "trend":
            trend

    })


# ============================================================
# CHARTS.JSON
# ============================================================

charts_data = {

    "station":
        STATION,

    "station_url":
        f"https://laut.fm/{STATION}",

    "title":
        "Discofox & Schlager Charts",

    "week":
        current_week,

    "previous_week":
        previous_week,

    "updated":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "charts":
        charts

}


# ============================================================
# DATEIEN SPEICHERN
# ============================================================

save_json(
    STATS_FILE,
    stats
)


save_json(
    CHARTS_FILE,
    charts_data
)


# ============================================================
# AUSGABE
# ============================================================

print("")
print(
    "=========================================="
)
print(
    "UPDATE ERFOLGREICH"
)
print(
    "=========================================="
)

print(
    f"Woche: {current_week}"
)

print(
    f"Vorwoche: {previous_week}"
)

print(
    f"Neue Plays: {new_plays}"
)

print(
    f"Bereits bekannte Einträge: {old_entries}"
)

print(
    f"Gefilterte Nicht-Musik-Einträge: "
    f"{ignored_entries}"
)

print(
    f"Songs in den Charts: {len(charts)}"
)

print("")


# ============================================================
# TOP 20 AUSGEBEN
# ============================================================

for item in charts:

    trend_text = ""

    if item["trend"] == "up":

        trend_text = (
            f"▲ +{item['movement']}"
        )

    elif item["trend"] == "down":

        trend_text = (
            f"▼ {item['movement']}"
        )

    elif item["trend"] == "same":

        trend_text = "▬"

    else:

        trend_text = "NEU"


    print(

        f'{item["position"]:02d}. '
        f'{item["artist"]} - '
        f'{item["title"]} | '
        f'{item["plays"]} Plays | '
        f'{trend_text}'

    )

print("")
print(
    "Charts gespeichert."
)
