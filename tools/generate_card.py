"""Generate dark_mode.svg / light_mode.svg for the profile card.

The card is a neofetch-style readout: ASCII portrait on the left, key/value rows
on the right, values right-aligned to a fixed column by a run of dots. today.py
rewrites the dynamic values (and their dot runs) on a schedule; everything else
is baked here.
"""
from xml.sax.saxutils import escape

W, H = 1010, 530
TEXT_X = 418          # right column origin, clears the 39-col portrait
WIDTH = 60            # right column width, in characters
ASCII_X, ROW_H, TOP = 15, 20, 30

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff",
                          add="#3fb950", dele="#f85149", cc="#616e7f", art="ascii_dark.txt"),
    "light_mode.svg": dict(bg="#f6f8fa", fg="#24292f", key="#953800", value="#0a3069",
                           add="#1a7f37", dele="#cf222e", cc="#c2cfde", art="ascii_light.txt"),
}

# (key, value, element_id) -- element_id set means today.py owns the value.
# A bare string is a section rule; None is a blank line.
ROWS = [
    ("@header", "basil@suhail", None),
    ("OS", "macOS, Arch Linux, Raspberry Pi OS", None),
    ("Uptime", "0 years, 0 months, 0 days", "age_data"),
    ("Host", "University of Aberdeen", None),
    ("Kernel", "MSc Data Science & Business Management", None),
    ("IDE", "VS Code, Antigravity, Warp, Claude Code", None),
    (None, None, None),
    ("Languages.Programming", "Python, TypeScript, SQL, R", None),
    ("Languages.Computer", "HTML, CSS, JSON, YAML, Markdown", None),
    ("Languages.Real", "English, Urdu", None),
    (None, None, None),
    ("Hobbies.Software", "agentic pipelines, self-hosting, OSINT", None),
    ("Hobbies.Hardware", "Raspberry Pi homelab, home servers", None),
    (None, None, None),
    ("@rule", "Contact", None),
    ("Email.Personal", "basilsuhailkhan@gmail.com", None),
    ("Portfolio", "basilsuhail.com", None),
    ("LinkedIn", "basilsuhail", None),
    (None, None, None),
    ("@rule", "GitHub Stats", None),
    ("Repos", "0", "repo_data"),
    ("Repos.Contributed", "0", "contrib_data"),
    ("Commits", "0", "commit_data"),
    ("@loc", None, None),
    ("@churn", None, None),
]


def dots(pad):
    """Match today.py's justify_format() so the bot's rewrites stay aligned."""
    if pad <= 2:
        return {0: "", 1: " ", 2: ". "}[max(0, pad)]
    return " " + ("." * pad) + " "


def key_span(key, colour):
    """Split dotted keys into per-segment tspans, as the neofetch look does."""
    parts = key.split(".")
    return ".".join(f'<tspan class="key">{escape(p)}</tspan>' for p in parts)


def row_svg(y, key, value, el_id):
    if key is None:
        return f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'

    if key == "@header":
        rule = "-" + "—" * (WIDTH - len(value) - 6) + "-—-"
        return (f'<tspan x="{TEXT_X}" y="{y}">{escape(value)}</tspan> {rule}')

    if key == "@rule":
        label = f"- {value} "
        rule = "-" + "—" * (WIDTH - len(label) - 5) + "-—-"
        return f'<tspan x="{TEXT_X}" y="{y}">{escape(label.rstrip())}</tspan> {rule}'

    if key == "@loc":
        return (
            f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">Lines of Code on GitHub</tspan>:'
            f'<tspan class="cc" id="loc_data_dots"> ......... </tspan>'
            f'<tspan class="value" id="loc_data">0</tspan>'
        )

    if key == "@churn":
        # added/removed share a line; loc_add carries the alignment for both,
        # so today.py sizes its dot run against the length of the removed count
        return (
            f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">Lines of Code</tspan>.<tspan class="key">Churn</tspan>:'
            f'<tspan class="cc" id="loc_add_dots"> ......... </tspan>'
            f'<tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, '
            f'<tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan>'
        )

    pad = WIDTH - 2 - len(key) - 1 - len(value)
    dot_run = dots(pad)
    dot_id = f' id="{el_id}_dots"' if el_id else ""
    val_id = f' id="{el_id}"' if el_id else ""
    return (
        f'<tspan x="{TEXT_X}" y="{y}" class="cc">. </tspan>'
        f'{key_span(key, None)}:'
        f'<tspan class="cc"{dot_id}>{dot_run}</tspan>'
        f'<tspan class="value"{val_id}>{escape(value)}</tspan>'
    )


def build(filename, theme):
    with open(theme["art"]) as f:
        art = f.read().split("\n")

    art_spans = "\n".join(
        f'<tspan x="{ASCII_X}" y="{TOP + i * ROW_H}">{escape(line)}</tspan>'
        for i, line in enumerate(art)
    )
    rows = "\n".join(
        row_svg(TOP + i * ROW_H, k, v, e) for i, (k, v, e) in enumerate(ROWS)
    )

    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{W}px" height="{H}px" font-size="16px">
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
</style>
<rect width="{W}px" height="{H}px" fill="{theme['bg']}" rx="15"/>
<text x="{ASCII_X}" y="{TOP}" fill="{theme['fg']}" class="ascii">
{art_spans}
</text>
<text x="{TEXT_X}" y="{TOP}" fill="{theme['fg']}">
{rows}
</text>
</svg>"""
    with open(filename, "w") as f:
        f.write(svg)
    return svg


def lengths():
    """The `length` argument today.py must pass for each dynamic field."""
    out = {}
    for key, value, el_id in ROWS:
        if el_id:
            out[el_id] = WIDTH - 4 - len(key) - 1
    return out


if __name__ == "__main__":
    for name, theme in THEMES.items():
        build(name, theme)
        print("wrote", name)
    print("justify_format lengths:", lengths())
