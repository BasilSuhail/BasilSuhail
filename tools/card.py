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
"""
import datetime
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

W, H = 1000, 595
TEXT_X = 418          # right column origin, clears the 39-col portrait
WIDTH = 60            # right column width, in characters
ASCII_X, ROW_H, TOP = 15, 20, 30

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff",
                          add="#3fb950", dele="#f85149", cc="#616e7f", art="ascii_dark.txt"),
    "light_mode.svg": dict(bg="#f6f8fa", fg="#24292f", key="#953800", value="#0a3069",
                           add="#1a7f37", dele="#cf222e", cc="#c2cfde", art="ascii_light.txt"),
}

# ('key', 'value') pairs. '@'-prefixed keys are handled specially below.
ROWS = [
    ("@header", "basil@suhail"),
    ("OS", "macOS / Raspberry Pi OS"),
    ("@uptime", None),
    ("Host", "MacBook Pro M4 Pro (24 GB), Edinburgh UK"),
    ("Kernel", "basil-ai 4.2.0-fintech"),
    ("Shell", "freelance 2.0 (AI dev, data, fintech)"),
    ("Packages", "2 (degrees), 9 (certs), 2 (awards)"),
    ("IDE", "VS Code, Antigravity, Warp, Claude Code"),
    (None, None),
    ("Languages.Programming", "Python, TypeScript, JS, SQL"),
    ("Languages.Computer", "HTML, CSS, JSON, YAML, Markdown"),
    ("Languages.Real", "English, Urdu"),
    (None, None),
    ("Hobbies.Software", "agentic pipelines, self-hosting, OSINT"),
    ("Hobbies.Hardware", "Raspberry Pi homelab, home servers"),
    ("Hobbies.Offline", "endurance running, triathlon"),
    (None, None),
    ("@rule", "Contact"),
    ("Email.Personal", "basilsuhailkhan@gmail.com"),
    ("Portfolio", "basilsuhail.com"),
    ("LinkedIn", "basilsuhail"),
    (None, None),
    ("@rule", "GitHub Stats"),
    ("Repos", "@repos"),
    ("Repos.Contributed", "@contrib"),
    ("Commits", "@commits"),
    ("Lines of Code on GitHub", "@loc"),
    ("@churn", None),
]

BIRTHDAY = datetime.datetime(2000, 1, 3)


def dots(pad):
    if pad <= 2:
        return {0: "", 1: " ", 2: ". "}[max(0, pad)]
    return " " + ("." * pad) + " "


def key_span(key):
    return ".".join(f'<tspan class="key">{escape(p)}</tspan>' for p in key.split("."))


CHAR_W = 9.592   # Consolas advance at 16px with the 109% size-adjust above


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


def uptime_row(y, now):
    """'XX years, XX months, XX days, HH:MM:SS' with a ticking HH:MM:SS.

    Returns the line itself plus the absolutely positioned clock elements, which
    the caller drops outside the <text> block.
    """
    from dateutil import relativedelta

    diff = relativedelta.relativedelta(now, BIRTHDAY)
    date_part = '{} {}, {} {}, {} {}{}'.format(
        diff.years, 'year' + ('' if diff.years == 1 else 's'),
        diff.months, 'month' + ('' if diff.months == 1 else 's'),
        diff.days, 'day' + ('' if diff.days == 1 else 's'),
        ' 🎂' if (diff.months == 0 and diff.days == 0) else '')

    # the clock is a fixed 8 characters wide plus a space of slack, so the dot
    # run stays put no matter what the clock reads
    clock_cols = len(" HH:MM:SS") + 1
    pad = WIDTH - 2 - len("Uptime") - 1 - len(date_part) - 1 - clock_cols
    line = (
        f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">Uptime</tspan>:'
        f'<tspan class="cc">{dots(pad)}</tspan>'
        f'<tspan class="value">{escape(date_part)},</tspan>'
    )

    two = [f"{i:02d}" for i in range(60)]
    extras = []
    # each group is right-anchored, so the end columns have to leave room for the
    # group that follows: 'SS' is 2 wide, 'MM:' and 'HH:' are 3
    extras += odometer([f"{i:02d}:" for i in range(24)], diff.hours, 3600,
                       diff.minutes * 60 + diff.seconds, WIDTH - 5, y, "h24")
    extras += odometer([f"{m}:" for m in two], diff.minutes, 60, diff.seconds,
                       WIDTH - 2, y, "m60")
    extras += odometer(two, diff.seconds, 1, 0, WIDTH, y, "s60")
    return line, extras


def row_svg(y, key, value, data, now):
    """Returns (line, extras); extras are elements that live outside <text>."""
    if key is None:
        return f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>', []

    if key == "@header":
        return f'<tspan x="{TEXT_X}" y="{y}">{escape(value)}</tspan> -' + "—" * (WIDTH - len(value) - 6) + "-—-", []

    if key == "@rule":
        label = f"- {value}"
        return f'<tspan x="{TEXT_X}" y="{y}">{escape(label)}</tspan> -' + "—" * (WIDTH - len(label) - 6) + "-—-", []

    if key == "@uptime":
        return uptime_row(y, now)

    if key == "@churn":
        add, dele = data["loc_add"], data["loc_del"]
        text = f"{add}++, {dele}--"
        pad = WIDTH - 2 - len("Lines of Code.Churn") - 1 - len(text)
        return (
            f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">Lines of Code</tspan>.<tspan class="key">Churn</tspan>:'
            f'<tspan class="cc">{dots(pad)}</tspan>'
            f'<tspan class="addColor">{add}++</tspan>, '
            f'<tspan class="delColor">{dele}--</tspan>'
        ), []

    if value.startswith("@"):
        value = data[value[1:]]

    pad = WIDTH - 2 - len(key) - 1 - len(value)
    return (
        f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
        f'{key_span(key)}:'
        f'<tspan class="cc">{dots(pad)}</tspan>'
        f'<tspan class="value">{escape(value)}</tspan>'
    ), []


def render(data, now=None):
    """Write both SVGs. `data` holds the GitHub numbers, already comma-formatted."""
    now = now or datetime.datetime.now()
    written = []
    for filename, theme in THEMES.items():
        with open(os.path.join(HERE, theme["art"])) as f:
            art = f.read().split("\n")

        # the portrait is shorter than the field list, so centre it vertically
        art_top = TOP + ((len(ROWS) - len(art)) // 2) * ROW_H
        art_spans = "\n".join(
            f'<tspan x="{ASCII_X}" y="{art_top + i * ROW_H}">{escape(line)}</tspan>'
            for i, line in enumerate(art)
        )
        lines, extras = [], []
        for i, (k, v) in enumerate(ROWS):
            line, extra = row_svg(TOP + i * ROW_H, k, v, data, now)
            lines.append(line)
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
