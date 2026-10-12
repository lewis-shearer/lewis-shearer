#!/usr/bin/env python3
"""Draw assets/readme.svg: a terminal-style profile card built from public GitHub data.

Stdlib only. Set GITHUB_TOKEN to raise API rate limits (the Actions token is enough).
"""
import datetime as dt
import html
import json
import os
import re
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = json.loads((ROOT / "data/profile.json").read_text())
STACK = json.loads((ROOT / "data/stack.json").read_text())
TOKENS_FILE = ROOT / "data/tokens.json"
OUT = ROOT / "assets/readme.svg"

USER = PROFILE["github_user"]
W = 850
PAD = 24
FG, MID, DIM, LINE, BG, TRACK = "#ededed", "#a3a3a3", "#5f5f5f", "#2a2a2a", "#0a0a0a", "#161616"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


# ---------- http ----------

def fetch(url, accept="application/vnd.github+json"):
    headers = {"User-Agent": f"{USER}-readme-card", "Accept": accept}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read().decode()


def fetch_json(url):
    return json.loads(fetch(url))


# ---------- data ----------

def contributions():
    """Daily counts for the last year, scraped from the public contribution calendar."""
    page = fetch(f"https://github.com/users/{USER}/contributions", accept="text/html")
    dates = dict(re.findall(r'data-date="([\d-]+)" id="([^"]+)"', page))
    dates = {cid: d for d, cid in dates.items()}
    counts = {}
    for cid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        if cid in dates:
            m = re.match(r"(\d+) contribution", text)
            counts[dates[cid]] = int(m.group(1)) if m else 0
    days = sorted((dt.date.fromisoformat(d), c) for d, c in counts.items())
    return days


def streaks(days):
    best = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        best = max(best, run)
    current = 0
    rev = list(reversed(days))
    if rev and rev[0][1] == 0:  # today not counted yet doesn't break the streak
        rev = rev[1:]
    for _, c in rev:
        if not c:
            break
        current += 1
    return current, best


def own_repos():
    repos = fetch_json(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    return [r for r in repos if not r["fork"]]


def languages(repos):
    skip = set(PROFILE.get("ignore_languages", []))
    total = Counter()
    for r in repos:
        for lang, n in fetch_json(r["languages_url"]).items():
            if lang not in skip:
                total[lang] += n
    s = sum(total.values()) or 1
    return [(lang.lower(), n / s * 100) for lang, n in total.most_common(6)]


def icons():
    groups = []
    for group in STACK["groups"]:
        out = []
        for item in group:
            slug = item if isinstance(item, str) else item["slug"]
            try:
                svg = fetch(f"https://cdn.simpleicons.org/{slug}", accept="image/svg+xml")
            except Exception as e:
                print(f"skip icon {slug}: {e}")
                continue
            fill = re.search(r'fill="(#[0-9A-Fa-f]{6})"', svg).group(1)
            if isinstance(item, dict) and item.get("color"):
                fill = item["color"]
            if luminance(fill) < 0.2:
                fill = FG  # near-black brands vanish on the dark card
            out.append((fill, re.search(r'<path d="([^"]+)"', svg).group(1)))
        if out:
            groups.append(out)
    return groups


def luminance(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------- pixel font ----------

GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".####|#....|#....|#....|#....|#....|.####", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".####|#....|#....|#..##|#...#|#...#|.####", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "#####|..#..|..#..|..#..|..#..|..#..|#####", "J": "..###|....#|....#|....#|#...#|#...#|.###.",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "#...#|#...#|#...#|#####|....#|....#|....#", "5": "#####|#....|#....|####.|....#|....#|####.",
    "6": ".###.|#....|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|..#..|..#..|..#..",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|....#|.###.",
    ",": "..|..|..|..|..|.#|#.", ".": ".|.|.|.|.|.|#", "-": "...|...|...|###|...|...|...",
    " ": "...|...|...|...|...|...|...",
}


def pixel_path(text, x, y, s):
    """Return (path d, width) for text drawn in the 5x7 font at pixel size s."""
    d, cx = [], x
    for ch in text.upper():
        rows = GLYPHS.get(ch, GLYPHS[" "]).split("|")
        for ry, row in enumerate(rows):
            for m in re.finditer(r"#+", row):
                w = len(m.group()) * s
                d.append(f"M{cx + m.start() * s} {y + ry * s}h{w}v{s}h-{w}z")
        cx += (len(rows[0]) + 1) * s
    return "".join(d), cx - x - s


def pixel_text(text, x, y, s, shadow=True):
    d, w = pixel_path(text, x, y, s)
    out = f'<path fill="url(#sh)" transform="translate({s} {s})" d="{d}"/>' if shadow else ""
    return out + f'<path fill="{FG}" d="{d}"/>', w


# ---------- svg helpers ----------

def text(x, y, s, size=12, fill=FG, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" {extra}>{s}</text>')


def label(x, y, title, note=""):
    note = f'<tspan fill="{DIM}" letter-spacing="0">  ·  {html.escape(note)}</tspan>' if note else ""
    return text(x, y, title, fill=MID, extra='letter-spacing=".6"').replace("</text>", note + "</text>")


def rule(y, x1=0, x2=W):
    return f'<line x1="{x1}" x2="{x2}" y1="{y + .5}" y2="{y + .5}" stroke="{LINE}" stroke-dasharray="4 3"/>'


def vrule(x, y1, y2):
    return f'<line x1="{x + .5}" x2="{x + .5}" y1="{y1}" y2="{y2}" stroke="{LINE}" stroke-dasharray="4 3"/>'


def bar(x, y, w, h, frac):
    """Track with a solid fill and a dithered leading edge, like a loading bar."""
    fill = max(0, min(1, frac)) * w
    edge = min(6, fill)
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{TRACK}"/>'
    for tx in range(1, 10):  # faint tick marks
        out += f'<rect x="{x + w * tx / 10:.1f}" y="{y + h - 2}" width="1" height="2" fill="{LINE}"/>'
    if fill - edge > 0:
        out += f'<rect x="{x}" y="{y}" width="{fill - edge:.1f}" height="{h}" fill="{FG}"/>'
    if edge:
        out += f'<rect x="{x + fill - edge:.1f}" y="{y}" width="{edge:.1f}" height="{h}" fill="url(#d50)"/>'
    return out


DEFS = f"""<defs>
<pattern id="d25" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="{FG}"/></pattern>
<pattern id="d50" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="{FG}"/><rect x="1" y="1" width="1" height="1" fill="{FG}"/></pattern>
<pattern id="d75" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="2" height="1" fill="{FG}"/><rect y="1" width="1" height="1" fill="{FG}"/></pattern>
<pattern id="sh" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="#4d4d4d"/><rect x="1" y="1" width="1" height="1" fill="#4d4d4d"/></pattern>
</defs>"""


# ---------- sections ----------

def header(y):
    out = text(PAD, y + 23, USER, size=13, extra='font-weight="700"')
    out += text(W - PAD, y + 23, f'~/<tspan fill="{FG}">readme</tspan>', size=13, fill=DIM, anchor="end")
    out += rule(y + 36)
    name, w = pixel_text(PROFILE["display_name"], PAD, y + 60, 6)
    out += name
    out += (f'<rect x="{PAD + w + 12}" y="{y + 60}" width="18" height="42" fill="{FG}">'
            '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" '
            'dur="1.1s" repeatCount="indefinite"/></rect>')
    out += text(PAD, y + 128, html.escape(PROFILE.get("tagline", "")), size=12, fill=MID)
    return out + rule(y + 146), 146


def stack(y, groups):
    n = sum(len(g) for g in groups)
    out = label(PAD, y + 24, "STACK", f"{n} tools")
    size, gap, sep = 26, 10, 18
    # wrap groups onto rows that fit the card
    rows, row, roww = [], [], 0
    for g in groups:
        gw = len(g) * (size + gap) - gap
        if row and roww + sep + gw > W - 2 * PAD:
            rows.append(row)
            row, roww = [], 0
        roww += (sep if row else 0) + gw
        row.append(g)
    rows.append(row)
    cy = y + 46
    for row in rows:
        roww = sum(len(g) * (size + gap) - gap for g in row) + sep * (len(row) - 1)
        cx = (W - roww) / 2
        for gi, g in enumerate(row):
            if gi:
                out += f'<rect x="{cx + sep / 2 - 1.5 - gap / 2 + gap / 2:.1f}" y="{cy + size / 2 - 1.5}" width="3" height="3" fill="{DIM}"/>'
                cx += sep
            for fill, d in g:
                out += f'<g transform="translate({cx:.1f} {cy}) scale({size / 24})"><path fill="{fill}" d="{d}"/></g>'
                cx += size + gap
            cx -= gap
        cy += size + 16
    h = cy - y + 8
    return out + rule(y + h), h


def activity(y, days):
    total = sum(c for _, c in days)
    current, best = streaks(days)
    out = label(PAD, y + 24, "CONTRIBUTIONS", f"{total:,} in the last year")
    # heatmap: columns are weeks, rows are weekdays
    cell, step = 7, 9
    first = days[0][0]
    offset = (first.weekday() + 1) % 7  # sunday-first like github
    peak = max((c for _, c in days), default=0) or 1
    gx, gy = PAD, y + 44
    months_drawn = set()
    for i, (d, c) in enumerate(days):
        col, row = divmod(i + offset, 7)
        x, yy = gx + col * step, gy + row * step
        lvl = 0 if c == 0 else min(4, 1 + int(3 * c / peak))
        fill = {0: TRACK, 1: "url(#d25)", 2: "url(#d50)", 3: "url(#d75)", 4: FG}[lvl]
        out += f'<rect x="{x}" y="{yy}" width="{cell}" height="{cell}" fill="{fill}"/>'
        if d.day <= 7 and row == 0 and d.month not in months_drawn and col < 51:
            months_drawn.add(d.month)
            out += text(x, gy + 7 * step + 16, d.strftime("%b").lower(), size=10, fill=DIM)
    # totals column
    tx = 540
    out += vrule(tx - 18, y, y + 150)
    out += label(tx, y + 24, "TOTALS")
    for i, (val, what) in enumerate([(total, "contributions"), (current, "day streak, current"), (best, "day streak, best")]):
        yy = y + 42 + i * 28
        num, _ = pixel_text(f"{val:,}", tx, yy, 3, shadow=False)
        out += num + text(tx + 110, yy + 16, what, size=12, fill=MID)
    out += bar(tx, y + 128, 200, 12, current / best if best else 0)
    out += text(W - PAD, y + 139, f"{current}/{best}", size=12, anchor="end")
    return out + rule(y + 150), 150


def langs_and_community(y, langs):
    out = label(PAD, y + 24, "LANGUAGES", PROFILE.get("languages_note", "by bytes"))
    for i, (lang, pct) in enumerate(langs):
        yy = y + 50 + i * 22
        out += text(PAD, yy + 9, html.escape(lang), size=12)
        out += bar(PAD + 118, yy, 180, 11, pct / 100)
        out += text(PAD + 360, yy + 9, f"{pct:.1f}%", size=12, anchor="end")
    rx = 420
    c = PROFILE.get("community", {})
    events = c.get("events", [])[:7]
    out += label(rx, y + 24, "COMMUNITY", "lifetime")
    cx = rx
    for n, what in ((c.get("talks", 0), "talks"), (c.get("workshops", 0), "workshops")):
        num, w = pixel_text(str(n), cx, y + 44, 4)
        out += num + text(cx + w + 10, y + 70, what, size=12)
        cx += w + 10 + len(what) * 7.3 + 28
    out += text(rx, y + 88, html.escape(c.get("role", "")), size=11, fill=DIM)
    start = y + 112
    for i, e in enumerate(events):
        yy = start + i * 18
        where = f'<tspan fill="{DIM}">  {html.escape(e.get("where", ""))}</tspan>' if e.get("where") else ""
        out += text(rx, yy, html.escape(e["what"]) + where, size=12)
        out += text(W - PAD, yy, html.escape(e.get("when", "")), size=11, fill=DIM, anchor="end")
    items = events
    h = max(50 + len(langs) * 22, (start - y) + len(items) * 18) + 10
    out += vrule(rx - 18, y, y + h)
    return out + rule(y + h), h


def token_spend(y):
    if not TOKENS_FILE.exists():
        return "", 0
    t = json.loads(TOKENS_FILE.read_text())
    total = int(t["total"])
    since = dt.date.fromisoformat(t["since"]).strftime("%b %Y").lower()
    synced = dt.datetime.fromisoformat(t["synced"]).strftime("%b %-d").lower()
    out = label(PAD, y + 24, "ESTIMATED TOKEN SPEND 😂", f"since {since}  ·  synced {synced}")
    num, w = pixel_text(f"{total:,}", PAD, y + 42, 5)
    out += num
    out += text(PAD + w + 24, y + 70, f"≈ {human(total)} tokens", size=13, fill=MID)
    goal = next_goal(total)
    out += bar(PAD, y + 92, 690, 14, total / goal)
    out += text(W - PAD, y + 104, f"{short(total)}/{short(goal)}", size=13, anchor="end")
    return out + rule(y + 122), 122


def next_goal(n):
    mag = 1
    while True:
        for m in (1, 2, 5):
            if m * mag > n:
                return m * mag
        mag *= 10


def human(n):
    for v, word in ((1e9, "billion"), (1e6, "million"), (1e3, "thousand")):
        if n >= v:
            return f"{n / v:.2f} {word}"
    return str(n)


def short(n):
    for v, s in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= v:
            return f"{n / v:.1f}".rstrip("0").rstrip(".") + s
    return str(n)


def footer(y):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M utc")
    out = f'<rect x="{PAD}" y="{y + 15}" width="6" height="6" fill="{FG}"/>'
    out += text(PAD + 14, y + 22, "regenerated every 6h by github actions", size=11, fill=DIM)
    out += text(W - PAD, y + 22, f"last sync {now}", size=11, fill=DIM, anchor="end")
    return out, 36


def main():
    repos = own_repos()
    sections = [
        header,
        lambda y: stack(y, icons()),
        lambda y: activity(y, contributions()),
        lambda y: langs_and_community(y, languages(repos)),
        token_spend,
        footer,
    ]
    body, y = [], 0
    for draw in sections:
        svg, h = draw(y)
        body.append(svg)
        y += h
    alt = f"{PROFILE['display_name']}: stack, contributions, languages, community"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{y}" viewBox="0 0 {W} {y}" '
           f'role="img" aria-label="{html.escape(alt)}">{DEFS}'
           f'<rect width="{W}" height="{y}" fill="{BG}"/>{"".join(body)}</svg>')
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg)
    print(f"wrote {OUT} ({len(svg) // 1024} KB, {W}x{y})")


if __name__ == "__main__":
    main()
