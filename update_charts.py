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
# VERZEICHNIS ERSTELLEN
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

    except Exception:

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
# AKTUELLE ISO-WOCHE
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

    value = str(value).strip()

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
# SONG-ID
# ============================================================

def song_id(song):

    artist_data = song.get(
        "artist",
        {}
    )

    artist = (
        artist_data.get(
            "name",
            ""
        )
        or "Unbekannter Künstler"
    ).strip()

    title = (
        song.get(
            "title",
            ""
        )
        or "Unbekannter Titel"
    ).strip()

    return (
        artist.lower()
        + "|||"
        + title.lower()
    )


# ============================================================
# EINZELNER PLAY
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
# LAUT.FM API ABRUFEN
# ============================================================

print(
    f"Lade laut.fm Daten für: {STATION}"
)

request = urllib.request.Request(

    API_URL,

    headers={
        "User-Agent":
            "Discofoxundschlager-Charts/1.0"
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
        "Fehler beim Abrufen der laut.fm API:"
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
        "Die API hat keine gültige Songliste geliefert."
    )

    raise SystemExit(1)


print(
    f"{len(data)} Songs von laut.fm erhalten."
)


# ============================================================
# STATISTIK LADEN
# ============================================================

stats = load_json(

    STATS_FILE,

    {
        "current_week":
            get_current_week(),

        "weeks": {},

        "processed_plays": []
    }
)


# ============================================================
# DATENSTRUKTUR SICHERSTELLEN
# ============================================================

if "weeks" not in stats:

    stats["weeks"] = {}


if "processed_plays" not in stats:

    stats["processed_plays"] = []


# ============================================================
# AKTUELLE WOCHE
# ============================================================

current_week = get_current_week()


# ============================================================
# WOCHENWECHSEL
# ============================================================

if stats.get(
    "current_week"
) != current_week:

    print(
        "Neue Chartwoche erkannt:"
    )

    print(
        f'{stats.get("current_week")} '
        f'-> {current_week}'
    )

    stats["current_week"] = current_week


# ============================================================
# AKTUELLE WOCHE ANLEGEN
# ============================================================

if current_week not in stats["weeks"]:

    stats["weeks"][current_week] = {}


# ============================================================
# BEREITS VERARBEITETE PLAYS
# ============================================================

processed = set(
    stats["processed_plays"]
)


new_plays = 0


# ============================================================
# SONGS VERARBEITEN
# ============================================================

for song in data:

    if not isinstance(
        song,
        dict
    ):

        continue


    # Startzeit des Plays

    started_at = song.get(
        "started_at"
    )


    if not started_at:

        continue


    # Datum umwandeln

    parsed_date = parse_date(
        started_at
    )


    if parsed_date is None:

        continue


    # Eindeutige Play-ID

    current_play_id = play_id(
        song
    )


    # Wurde dieser Play bereits gezählt?

    if current_play_id in processed:

        continue


    # Play speichern

    processed.add(
        current_play_id
    )


    # Künstler

    artist_data = song.get(
        "artist",
        {}
    )


    artist = (
        artist_data.get(
            "name",
            ""
        )
        or "Unbekannter Künstler"
    ).strip()


    # Titel

    title = (
        song.get(
            "title",
            ""
        )
        or "Unbekannter Titel"
    ).strip()


    # Woche des Plays

    play_week = parsed_date.strftime(
        "%G-W%V"
    )


    # Woche anlegen

    if play_week not in stats["weeks"]:

        stats["weeks"][play_week] = {}


    week = stats[
        "weeks"
    ][play_week]


    # Song-ID

    identifier = song_id(
        song
    )


    # Song erstmalig anlegen

    if identifier not in week:

        week[identifier] = {

            "artist":
                artist,

            "title":
                title,

            "plays":
                0

        }


    # Play erhöhen

    week[identifier]["plays"] += 1


    new_plays += 1


# ============================================================
# PLAY-HISTORIE BEGRENZEN
# ============================================================

processed_list = list(
    processed
)


if len(processed_list) > 10000:

    processed_list = processed_list[
        -10000:
    ]


stats["processed_plays"] = (
    processed_list
)


# ============================================================
# NUR LETZTE 8 WOCHEN BEHALTEN
# ============================================================

all_weeks = sorted(
    stats["weeks"].keys(),
    reverse=True
)


for old_week in all_weeks[8:]:

    del stats[
        "weeks"
    ][old_week]


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


for song in current_week_data.values():

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

    key=lambda item:
        item["plays"],

    reverse=True

)


# ============================================================
# TOP 20
# ============================================================

chart_items = chart_items[
    :MAX_CHARTS
]


# ============================================================
# POSITIONEN VERGEBEN
# ============================================================

charts = []


for position, song in enumerate(

    chart_items,

    start=1

):

    charts.append({

        "position":
            position,

        "artist":
            song["artist"],

        "title":
            song["title"],

        "plays":
            song["plays"]

    })


# ============================================================
# VORWOCHE ERMITTELN
# ============================================================

sorted_weeks = sorted(

    stats["weeks"].keys(),

    reverse=True

)


previous_week = None


for week in sorted_weeks:

    if week < current_week:

        previous_week = week

        break


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
# ERGEBNIS AUSGEBEN
# ============================================================

print("")
print(
    "=========================================="
)

print(
    "Discofox & Schlager Charts"
)

print(
    "erfolgreich aktualisiert"
)

print(
    "=========================================="
)

print(
    f"Woche: {current_week}"
)

print(
    f"Neue Plays: {new_plays}"
)

print(
    f"Chartplätze: {len(charts)}"
)

print("")


# ============================================================
# TOP 10 AUSGEBEN
# ============================================================

for item in charts[:10]:

    print(

        f'{item["position"]}. '
        f'{item["artist"]} - '
        f'{item["title"]} '
        f'({item["plays"]} Plays)'

    )
