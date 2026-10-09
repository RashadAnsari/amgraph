"""The mechanical half of a legal review: has the law moved, and do the quotes still hold?

Reads docs/countries/<cc>.md, finds every wetten.overheid.nl act it links, asks
the site which version is in force today, and checks every quoted passage in the
document word for word against the current text of those acts.

It cannot do the review. A quote that is still present can sit in an article
whose meaning changed around it, and a quote from a municipal page or a
government site is not checked here at all. What it does is make the first
two steps impossible to skip or to do by eye.

Usage: uv run python .claude/skills/legal-review/check_statutes.py nl
Exit 1 when an act has a newer version or a statute quote is not found.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
ACT = re.compile(r"https://wetten\.overheid\.nl/(BWBR\d+)/(\d{4}-\d{2}-\d{2})")
#: A published act or decision: fixed once published, so a quote from it is
#: checked against it, not against the consolidated law in force.
PUBLICATION = re.compile(r"https://zoek\.officielebekendmakingen\.nl/[\w.-]+\.html")


def text_of(page: str) -> str:
    page = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    return normalise(html.unescape(re.sub(r"<[^>]+>", " ", page)))


def normalise(text: str) -> str:
    # Typographic quotes and apostrophes differ between the site and a hand-typed
    # quote without changing a word; whitespace differs with every reflow.
    for typographic, plain in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"')):
        text = text.replace(typographic, plain)
    return re.sub(r"\s+", " ", text).strip().lower()


PENDING = "wijziging(en) zonder datum inwerkingtreding aanwezig"


def fetch(url: str) -> requests.Response:
    response = requests.get(url, headers={"User-Agent": "amgraph legal review"}, timeout=120)
    response.raise_for_status()
    return response


def current(act: str) -> tuple[str, str]:
    """The version date in force today, and its normalised text."""
    response = fetch(f"https://wetten.overheid.nl/{act}")
    found = re.search(rf"/{act}/(\d{{4}}-\d{{2}}-\d{{2}})", response.url)
    if not found:
        raise SystemExit(f"{act}: the site did not redirect to a dated version ({response.url})")
    return found.group(1), text_of(response.text)


def quotes(document: str) -> list[tuple[int, str]]:
    """Every blockquote, joined across lines, with the line it starts on."""
    out: list[tuple[int, str]] = []
    block: list[str] = []
    start = 0
    for number, line in enumerate([*document.splitlines(), ""], 1):
        if line.startswith(">"):
            if not block:
                start = number
            block.append(line.lstrip("> ").strip())
        elif block:
            out.append((start, " ".join(block)))
            block = []
    return out


def fragments(quote: str) -> list[str]:
    """The quoted words, without the lid labels and ellipses added around them."""
    quote = re.sub(r"^(lid \d+|lid \w+):\s*", "", quote)
    parts = re.findall(r'"([^"]+)"', quote) or [quote]
    pieces: list[str] = []
    for part in parts:
        pieces.extend(p.strip(" .,;") for p in re.split(r"…|\.\.\.", part))
    return [normalise(p) for p in pieces if len(p.strip()) > 12]


def main(code: str) -> int:
    path = ROOT / "docs" / "countries" / f"{code}.md"
    document = path.read_text()
    linked = sorted(set(ACT.findall(document)))
    if not linked:
        print(f"{path}: links no wetten.overheid.nl act; check its sources by hand")
        return 0

    problems = 0
    texts: list[str] = []
    for act in sorted({a for a, _ in linked}):
        cited = sorted(d for a, d in linked if a == act)
        version, text = current(act)
        texts.append(text)
        if version != cited[-1]:
            problems += 1
            print(f"CHANGED  {act}: in force {version}, document cites {', '.join(cited)}")
        else:
            print(f"same     {act}: in force {version}, as cited")
        # An amendment already adopted and waiting for a royal decree. It binds
        # nobody yet, but it is the change most likely to arrive between two
        # reviews, so the review has to know what it says.
        if PENDING in text:
            problems += 1
            print(f"PENDING  {act}: carries amendments adopted without a commencement date;")
            print("         open an article's 'Wijzigingenoverzicht' to see which law, and")
            print("         record it in the country document if it touches a rule")

    for url in sorted(set(PUBLICATION.findall(document))):
        texts.append(text_of(fetch(url).text))

    for line, quote in quotes(document):
        missing = [f for f in fragments(quote) if not any(f in t for t in texts)]
        if missing:
            problems += 1
            print(f"NOT FOUND {path.name}:{line}: {missing[0][:90]!r}")
            print("          in no current statute or linked publication. Either the law")
            print("          changed or the quote comes from another source; check it by hand.")
    print(f"{len(quotes(document))} quotes checked, {problems} to look at")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "nl"))
