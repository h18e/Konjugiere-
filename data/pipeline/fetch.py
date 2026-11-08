"""Rohdaten herunterladen und dabei auf Verben der benötigten Sprachen filtern.

Die Wiktextract-Gesamtdateien sind mehrere GB gross. Sie werden deshalb nicht
gespeichert, sondern als Datenstrom gelesen: Nur die Einträge für Verben der
gewünschten Sprachen landen in einer kleinen JSONL-Datei.

Aufruf (aus dem Ordner data/):
    python3 -m pipeline.fetch enwiktionary
    python3 -m pipeline.fetch dewiktionary
    python3 -m pipeline.fetch verbiste
    python3 -m pipeline.fetch frequency
"""

from __future__ import annotations

import gzip
import json
import sys
import tarfile
import subprocess
from pathlib import Path
from typing import Iterable, Iterator

DATA_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = DATA_DIR / "raw"
USER_AGENT = "Konjugiere-datascript/0.1"

SOURCES = {
    "enwiktionary": {
        "url": "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz",
        "langs": {"fr", "it", "en"},
        "out": RAW_DIR / "enwiktionary" / "verbs.jsonl",
    },
    "dewiktionary": {
        "url": "https://kaikki.org/dewiktionary/raw-wiktextract-data.jsonl.gz",
        # de: deutsche Verben, deren Übersetzungstabellen die deutschen Bedeutungen liefern
        "langs": {"fr", "it", "en", "de"},
        "out": RAW_DIR / "dewiktionary" / "verbs.jsonl",
    },
}

VERBISTE_URL = "https://deb.debian.org/debian/pool/main/v/verbiste/verbiste_0.1.49.orig.tar.gz"


def curl_args(url: str) -> list[str]:
    return ["curl", "-sfL", "--retry", "3", "-A", USER_AGENT, url]


def keep_entry(entry: dict, langs: set[str]) -> bool:
    """True, wenn der Eintrag ein Verb in einer der gewünschten Sprachen ist."""
    return entry.get("pos") == "verb" and entry.get("lang_code") in langs


def filter_lines(lines: Iterable[str], langs: set[str]) -> Iterator[dict]:
    """Liest JSONL-Zeilen und gibt nur die passenden Einträge zurück.

    Ein schneller Textvergleich sortiert die meisten Zeilen aus, bevor das
    vergleichsweise langsame json.loads läuft.
    """
    for line in lines:
        if '"verb"' not in line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if keep_entry(entry, langs):
            yield entry


def stream_filter(name: str) -> None:
    src = SOURCES[name]
    out: Path = src["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    count = 0
    # curl statt urllib: curl nutzt die Zertifikate von macOS, das Python von
    # python.org bringt ohne Zusatzschritt keine mit.
    curl = subprocess.Popen(curl_args(src["url"]), stdout=subprocess.PIPE)
    with gzip.open(curl.stdout, "rt", encoding="utf-8") as lines, \
            tmp.open("w", encoding="utf-8") as fh:
        for entry in filter_lines(lines, src["langs"]):
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1
            if count % 5000 == 0:
                print(f"{name}: {count} Verbeinträge …", flush=True)
    if curl.wait() != 0:
        sys.exit(f"{name}: Download fehlgeschlagen (curl-Code {curl.returncode})")
    tmp.replace(out)
    print(f"{name}: fertig, {count} Verbeinträge in {out}")


FREQUENCY_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{lang}/{lang}_50k.txt"


def fetch_frequency() -> None:
    target = RAW_DIR / "frequency"
    target.mkdir(parents=True, exist_ok=True)
    for lang in ("fr", "it", "en", "de"):
        out = target / f"{lang}_50k.txt"
        subprocess.run(curl_args(FREQUENCY_URL.format(lang=lang)) + ["-o", str(out)], check=True)
    print(f"frequency: Listen in {target}")


def fetch_verbiste() -> None:
    target = RAW_DIR / "verbiste"
    target.mkdir(parents=True, exist_ok=True)
    archive = target / VERBISTE_URL.rsplit("/", 1)[1]
    if not archive.exists():
        subprocess.run(curl_args(VERBISTE_URL) + ["-o", str(archive)], check=True)
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers()
                   if m.isfile() and (m.name.endswith(".xml") or m.name.endswith("COPYING"))]
        tar.extractall(target, members=members, filter="data")
    print(f"verbiste: entpackt nach {target}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "verbiste":
        fetch_verbiste()
    elif what == "frequency":
        fetch_frequency()
    elif what in SOURCES:
        stream_filter(what)
    else:
        sys.exit("Aufruf: python3 -m pipeline.fetch [verbiste|frequency|enwiktionary|dewiktionary]")
