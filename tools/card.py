"""Build dark_mode.svg / light_mode.svg.

The card is a neofetch-style readout: ASCII portrait on the left, key/value rows
on the right, values right-aligned to a fixed column by a run of dots. today.py
calls render() with fresh numbers; nothing is patched in place, the whole file is
rewritten, so the dot alignment can never drift out of sync with the values.

The Uptime clock ticks. A README image cannot run JavaScript, so each of hh, mm
and ss is a stack of pre-rendered frames sitting at identical coordinates, and a
CSS keyframe gives each frame the one slot of the cycle where it is opaque. The
frames are separate <text> elements rather than tspans, because a tspan takes up
room in the line's text layout even while invisible and would shove the rest of
the line sideways.

The animation clock starts when the browser loads the image, not when the file
was built, so the ticking is only as accurate as the last workflow run -- see the
cron in build.yaml.

The portrait is coloured from the photograph itself: tools/make_ascii.py stores an
average colour per character cell alongside the glyphs, and adapt() pushes each
one into a brightness band that reads against the theme background while keeping
its hue, so the hair, skin, shirt and tie stay recognisably their own colours.
"""
import datetime
import json
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

W, H = 1050, 620
TEXT_X = 418          # right column origin, clears the 39-col portrait
WIDTH = 60            # right column width, in characters
ASCII_X, ROW_H, TOP = 15, 20, 30

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff",
                          add="#3fb950", dele="#f85149", cc="#616e7f",
                          site="#7ee787", social="#79c0ff", mail="#ffa198", pop="#d2a8ff",
                          lum=(0.38, 1.0), warm=0.16),
    "light_mode.svg": dict(bg="#f6f8fa", fg="#24292f", key="#953800", value="#0a3069",
                           add="#1a7f37", dele="#cf222e", cc="#c2cfde",
                           site="#1a7f37", social="#0969da", mail="#cf222e", pop="#8250df",
                           lum=(0.08, 0.58), warm=0.30),
}

# Rows whose value gets its own colour instead of the default blue.
ACCENTS = {
    "Portfolio": "site",
    "LinkedIn": "social",
    "Email.Personal": "mail",
    "Contributions": "pop",
    "Shell": "pop",
    "Hobbies.Offline": "site",
}

# ('key', 'value') pairs. '@'-prefixed keys are handled specially below.
ROWS = [
    ("@header", "basil@suhail"),
    ("OS", "macOS / Raspberry Pi OS"),
    ("@uptime", None),
    # Host is where this runs, Kernel is what it is built on (four years of
    # finance operations), Shell is the day job you actually interact with.
    ("Host", "Edinburgh, Scotland"),
    ("Kernel", "finance-ops 4.0.0-LTS"),
    ("Shell", "freelance 2.0 (AI dev, data, fintech)"),
    ("Locale", "en_GB.UTF-8"),
    ("Packages", "2 (degrees), 9 (certs), 2 (awards)"),
    ("IDE", "VS Code, Antigravity, Warp, Claude Code"),
    (None, None),
    ("Languages.Programming", "Python, TypeScript, JS, SQL"),
    ("Languages.Computer", "HTML, CSS, JSON, YAML, Markdown"),
    ("Languages.Real", "English, Urdu"),
    (None, None),
    ("Hobbies.Software", "agentic pipelines, self-hosting, OSINT"),
    ("Hobbies.Hardware", "Raspberry Pi homelab, home servers"),
    ("Hobbies.Offline", "running, triathlon, touching grass"),
    (None, None),
    ("@rule", "Contact"),
    ("Email.Personal", "basilsuhailkhan@gmail.com"),
    ("Portfolio", "basilsuhail.com"),
    ("LinkedIn", "basilsuhail"),
    (None, None),
    ("@rule", "GitHub Stats"),
    ("Repos.Public", "@repos"),
    ("Repos.Contributed", "@contrib"),
    ("Contributions", "@contributions"),
    ("Lines of Public Code", "@loc"),
    ("@churn", None),
]

# Uptime counts from the moment the GitHub account came up, not from a date of
# birth: this is the machine's uptime, not its owner's. today.py passes the real
# creation timestamp through render(); this is only the standalone fallback.
DEFAULT_SINCE = datetime.datetime(2025, 9, 23, 13, 36, 28)


def dots(pad):
    if pad <= 2:
        return {0: "", 1: " ", 2: ". "}[max(0, pad)]
    return " " + ("." * pad) + " "


def key_span(key):
    return ".".join(f'<tspan class="key">{escape(p)}</tspan>' for p in key.split("."))


# Every line is pinned to exactly this much width per character. The card cannot
# know which monospace font the viewer actually gets -- GitHub was rendering the
# text about 10% wider than Consolas, which pushed the right-hand end of every
# line outside the viewBox and cropped it -- so instead of trusting a metric, each
# line carries a textLength and the renderer is made to fit it.
CHAR_W = 10.0


def adapt(rgb, lum_range, saturate=2.0, warm=0.0):
    """Pull a colour sampled from the photo into a range readable on the card.

    Hue is preserved -- hair stays brown, tie stays navy, skin stays warm -- while
    the brightness is pushed into a band that reads against the background, and
    saturation is lifted because averaging a whole cell washes it out. `warm`
    then tilts the result towards amber, which a webcam frame under indoor light
    needs before it stops reading as grey.
    """
    r, g, b = (c / 255 for c in rgb)
    grey = 0.299 * r + 0.587 * g + 0.114 * b
    r, g, b = (grey + (c - grey) * saturate for c in (r, g, b))
    r, g, b = r * (1 + warm), g * (1 + warm * 0.35), b * (1 - warm * 0.9)
    lo, hi = lum_range
    target = lo + (hi - lo) * grey
    scale = target / max(grey, 0.02)
    r, g, b = (min(1.0, max(0.0, c * scale)) for c in (r, g, b))
    # quantise so neighbouring cells collapse into one run instead of one span each
    return "#%02x%02x%02x" % tuple(round(c * 255 / 24) * 24 for c in (r, g, b))


def portrait_spans(x, y, chars, colors, lum_range, warm):
    """One line of the portrait, split into runs of equal colour.

    Spaces stay in the string and inherit whatever colour is current. They are
    invisible either way, but dropping them would let textLength stretch the
    remaining glyphs across the whole line and scatter the picture.
    """
    # Indent by moving the line's origin rather than by emitting leading spaces:
    # whether leading whitespace survives depends on the renderer's whitespace
    # handling, whereas an x offset is unambiguous everywhere.
    lead = len(chars) - len(chars.lstrip(" "))
    x, chars, colors = x + lead * CHAR_W, chars[lead:], colors[lead:]

    runs, current, buf = [], None, ""
    for i, ch in enumerate(chars):
        colour = current if ch == " " else adapt(colors[i], lum_range, warm=warm)
        if colour != current and buf:
            runs.append((current, buf))
            buf = ""
        current, buf = colour, buf + ch
    if buf:
        runs.append((current, buf))

    # every run gets its own element, including the colourless leading spaces:
    # a bare whitespace text node sitting next to a child element gets dropped by
    # some renderers, which would shove the whole line back to the left margin
    inner = "".join(
        (f'<tspan fill="{c}">{escape(t)}</tspan>' if c else f'<tspan>{escape(t)}</tspan>')
        for c, t in runs
    )
    return fit(x, y, inner, len(chars))


def fit(x, y, inner, chars):
    """Place a line at (x, y) and force it to occupy exactly `chars` columns."""
    if chars <= 1:
        return f'<tspan x="{x}" y="{y}">{inner}</tspan>'
    return (f'<tspan x="{x}" y="{y}" textLength="{chars * CHAR_W:.1f}"'
            f' lengthAdjust="spacing">{inner}</tspan>')


def odometer(frames, start_index, slot_seconds, phase, end_col, y, css_class):
    """One clock field, as a stack of frames that take turns being opaque.

    Every frame sits at the same coordinates as its own <text>, so none of them
    take part in the line's text layout and none can shove the others sideways.
    A CSS keyframe holds each frame opaque for exactly one slot of the cycle and
    a negative animation-delay per frame staggers them into sequence. The frame
    that is current at build time keeps opacity 1 in the markup, so a renderer
    that ignores CSS animation still shows the right time, just frozen.
    """
    n = len(frames)
    cycle = n * slot_seconds
    x = TEXT_X + end_col * CHAR_W
    out = []
    for i in range(n):
        # frame i is due (i - start_index) slots from now; rewinding the clock by
        # that much (minus however far into the current slot we already are) puts
        # its opaque window exactly there. All delays stay negative, so every
        # frame is mid-animation from the first paint.
        steps = (i - start_index) % n
        delay = -((phase - steps * slot_seconds) % cycle)
        out.append(
            f'<text x="{x:.1f}" y="{y}" class="value {css_class}" text-anchor="end"'
            f' opacity="{1 if i == start_index else 0}"'
            f' style="animation-delay:{delay:.3f}s">{frames[i]}</text>'
        )
    return out


def uptime_row(y, now, since):
    """'XX years, XX months, XX days, HH:MM:SS' with a ticking HH:MM:SS.

    Returns the line itself plus the absolutely positioned clock elements, which
    the caller drops outside the <text> block.
    """
    from dateutil import relativedelta

    diff = relativedelta.relativedelta(now, since)
    date_part = '{} {}, {} {}, {} {}'.format(
        diff.years, 'year' + ('' if diff.years == 1 else 's'),
        diff.months, 'month' + ('' if diff.months == 1 else 's'),
        diff.days, 'day' + ('' if diff.days == 1 else 's'))

    # the clock is a fixed 8 characters wide plus a space of slack, so the dot
    # run stays put no matter what the clock reads
    clock_cols = len(" HH:MM:SS") + 1
    pad = WIDTH - 2 - len("Uptime") - 1 - len(date_part) - 1 - clock_cols
    line = (
        f'<tspan class="cc">. </tspan>'
        f'<tspan class="key">Uptime</tspan>:'
        f'<tspan class="cc">{dots(pad)}</tspan>'
        f'<tspan class="value">{escape(date_part)},</tspan>'
    )
    plain = f". Uptime:{dots(pad)}{date_part},"

    two = [f"{i:02d}" for i in range(60)]
    extras = []
    # each group is right-anchored, so the end columns have to leave room for the
    # group that follows: 'SS' is 2 wide, 'MM:' and 'HH:' are 3
    extras += odometer([f"{i:02d}:" for i in range(24)], diff.hours, 3600,
                       diff.minutes * 60 + diff.seconds, WIDTH - 5, y, "h24")
    extras += odometer([f"{m}:" for m in two], diff.minutes, 60, diff.seconds,
                       WIDTH - 2, y, "m60")
    extras += odometer(two, diff.seconds, 1, 0, WIDTH, y, "s60")
    return line, plain, extras


def row_svg(y, key, value, data, now, since):
    """Returns (inner, plain, extras).

    `inner` is the row's markup without any positioning, `plain` is the same row
    as flat text so the caller can measure it, and `extras` are elements that
    have to live outside the <text> block.
    """
    if key is None:
        return '<tspan class="cc">. </tspan>', ". ", []

    if key == "@header":
        rule = " -" + "—" * (WIDTH - len(value) - 6) + "-—-"
        return f'<tspan>{escape(value)}</tspan>{rule}', value + rule, []

    if key == "@rule":
        label = f"- {value}"
        rule = " -" + "—" * (WIDTH - len(label) - 6) + "-—-"
        return f'<tspan>{escape(label)}</tspan>{rule}', label + rule, []

    if key == "@uptime":
        return uptime_row(y, now, since)

    if key == "@churn":
        add, dele = data["loc_add"], data["loc_del"]
        text = f"{add}++, {dele}--"
        pad = WIDTH - 2 - len("Public Code.Churn") - 1 - len(text)
        return (
            f'<tspan class="cc">. </tspan>'
            f'<tspan class="key">Public Code</tspan>.<tspan class="key">Churn</tspan>:'
            f'<tspan class="cc">{dots(pad)}</tspan>'
            f'<tspan class="addColor">{add}++</tspan>, '
            f'<tspan class="delColor">{dele}--</tspan>'
        ), ". Public Code.Churn:" + dots(pad) + text, []

    if value.startswith("@"):
        value = data[value[1:]]

    pad = WIDTH - 2 - len(key) - 1 - len(value)
    accent = ACCENTS.get(key, "value")
    return (
        f'<tspan class="cc">. </tspan>'
        f'{key_span(key)}:'
        f'<tspan class="cc">{dots(pad)}</tspan>'
        f'<tspan class="{accent}">{escape(value)}</tspan>'
    ), f". {key}:{dots(pad)}{value}", []


def render(data, now=None):
    """Write both SVGs. `data` holds the GitHub numbers, already comma-formatted.

    data['since'] is the account creation timestamp that Uptime counts from,
    as returned by the API ('YYYY-MM-DDTHH:MM:SSZ').
    """
    now = now or datetime.datetime.now()
    since = (datetime.datetime.strptime(data['since'], '%Y-%m-%dT%H:%M:%SZ')
             if data.get('since') else DEFAULT_SINCE)
    written = []
    for filename, theme in THEMES.items():
        with open(os.path.join(HERE, "portrait.json")) as f:
            portrait = json.load(f)
        art, art_colors = portrait["chars"], portrait["colors"]

        # the portrait is shorter than the field list, so centre it vertically
        art_top = TOP + ((len(ROWS) - len(art)) // 2) * ROW_H
        art_spans = "\n".join(
            portrait_spans(ASCII_X, art_top + i * ROW_H, line, art_colors[i], theme["lum"], theme["warm"])
            for i, line in enumerate(art) if line.strip()
        )
        lines, extras = [], []
        for i, (k, v) in enumerate(ROWS):
            inner, plain, extra = row_svg(TOP + i * ROW_H, k, v, data, now, since)
            lines.append(fit(TEXT_X, TOP + i * ROW_H, inner, len(plain)))
            extras += extra
        rows = "\n".join(lines)
        clock = "\n".join(extras)

        svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}px" height="{H}px" font-family="ConsolasFallback,Consolas,monospace" font-size="16px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {theme['key']};}}
.value {{fill: {theme['value']};}}
.site {{fill: {theme['site']};}}
.social {{fill: {theme['social']};}}
.mail {{fill: {theme['mail']};}}
.pop {{fill: {theme['pop']};}}
.addColor {{fill: {theme['add']};}}
.delColor {{fill: {theme['dele']};}}
.cc {{fill: {theme['cc']};}}
text, tspan {{white-space: pre;}}
/* Each clock frame is opaque for exactly one slot of its cycle. The frames are
   staggered by negative animation-delay, so together they read as a ticker.
   steps(1,end) is what keeps the frame at full opacity for the whole slot --
   with a linear timing function the opacity would fade across the slot instead
   of holding, and two frames would be half-visible at once. */
@keyframes tick60 {{0%{{opacity:1}} 1.6666%{{opacity:0}} 100%{{opacity:0}}}}
@keyframes tick24 {{0%{{opacity:1}} 4.1666%{{opacity:0}} 100%{{opacity:0}}}}
.s60 {{animation: tick60 60s steps(1,end) infinite;}}
.m60 {{animation: tick60 3600s steps(1,end) infinite;}}
.h24 {{animation: tick24 86400s steps(1,end) infinite;}}
</style>
<rect width="{W}px" height="{H}px" fill="{theme['bg']}" rx="15"/>
<text x="{ASCII_X}" y="{TOP}" fill="{theme['fg']}" class="ascii">
{art_spans}
</text>
<text x="{TEXT_X}" y="{TOP}" fill="{theme['fg']}">
{rows}
</text>
{clock}
</svg>"""
        path = os.path.join(ROOT, filename)
        with open(path, "w") as f:
            f.write(svg)
        written.append(path)
    return written


if __name__ == "__main__":
    # preview with placeholder numbers
    render({"repos": "0", "contrib": "0", "commits": "0",
            "loc": "0", "loc_add": "0", "loc_del": "0"})
    print("wrote dark_mode.svg and light_mode.svg with placeholder stats")
