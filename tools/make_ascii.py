"""Convert the GitHub avatar into a Consolas-grid ASCII portrait.

The source photo is a webcam shot: bright uneven wall, mid-tone face, near-black
hair and suit. A naive luminance ramp turns the wall into noise and the suit into
a solid blob, so this does three things instead:

  1. flood-fills the background in from the border and masks it out entirely
  2. builds a local-contrast (detail) channel so large flat areas -- cheek, wall,
     jacket -- stay light and only real edges get dense glyphs
  3. blends detail with a gently compressed luminance channel so the portrait
     still reads as a face and not just an outline
"""
import sys
from PIL import Image, ImageOps, ImageFilter
import numpy as np

COLS, ROWS = 43, 25

# ink coverage ramp, sparse -> dense (no <, >, & so the SVG stays clean)
# A short ramp reads far better at this size than a long one. With 60+ glyphs
# the eye sees character noise instead of a face, because neighbouring cells
# pick visually unrelated shapes for nearly identical brightnesses.
RAMP = " .:-=+*#%@"


def background_mask(gray, tol=42):
    """Flood fill from the border; True where the pixel belongs to the subject.

    Every candidate is compared against a single global reference (the median of
    the border pixels) rather than against its neighbour -- comparing to the
    neighbour lets the fill creep down the wall's shading gradient and swallow
    the whole photo.
    """
    gray = gray.astype(np.float32)
    h, w = gray.shape
    border = np.concatenate([gray[0], gray[-1], gray[:, 0], gray[:, -1]])
    ref = float(np.median(border))

    candidate = np.abs(gray - ref) <= tol
    bg = np.zeros((h, w), dtype=bool)
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if candidate[y, x] and not bg[y, x]:
                bg[y, x] = True
                stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if candidate[y, x] and not bg[y, x]:
                bg[y, x] = True
                stack.append((y, x))

    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and candidate[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                stack.append((ny, nx))
    return ~bg


def build(path, cols=COLS, rows=ROWS, crop=(0.10, 0.00, 0.90, 0.94),
          detail_weight=0.10, floor=0.04, polarity="dark"):
    im = Image.open(path).convert("L")
    w, h = im.size
    im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    im = ImageOps.autocontrast(im, cutoff=1)

    arr = np.asarray(im, dtype=np.float32)
    subject = background_mask(np.asarray(im))

    # local contrast: how far each pixel sits from its neighbourhood average
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(radius=6)), dtype=np.float32)
    detail = np.abs(arr - blur)
    detail /= max(detail.max(), 1.0)
    detail = np.clip(detail * 2.6, 0, 1)

    # Glyph density has to track ink, and ink flips with the theme: on the dark
    # card the glyphs are light, so density must follow the *bright* parts of the
    # photo (skin, shirt); on the light card it must follow the dark parts.
    lum = arr / 255.0 if polarity == "dark" else 1.0 - (arr / 255.0)
    lum = np.clip((lum - 0.12) / 0.78, 0, 1) ** 1.25

    value = detail_weight * detail + (1 - detail_weight) * lum
    value = np.where(subject, np.clip(value + floor, 0, 1), 0.0)

    cell = Image.fromarray((value * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)
    grid = np.asarray(cell, dtype=np.float32) / 255.0
    grid = np.clip(grid * 1.15, 0, 1)

    lines = []
    for r in range(rows):
        row = "".join(RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))] for v in grid[r])
        lines.append(row.rstrip())
    return lines


def preview(lines, out, cols=COLS, rows=ROWS, dark=True):
    """Render the ASCII back to a PNG so the result can actually be looked at."""
    from PIL import ImageDraw, ImageFont
    cw, ch = 11, 22
    img = Image.new("RGB", (cols * cw + 20, rows * ch + 20), "#161b22" if dark else "#f6f8fa")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(lines):
        d.text((10, 10 + i * ch), line, font=font, fill="#c9d1d9" if dark else "#24292f")
    img.save(out)


if __name__ == "__main__":
    lines = build(sys.argv[1])
    print("\n".join(lines))
    if len(sys.argv) > 2:
        preview(lines, sys.argv[2])


def build_colored(path, cols=COLS, rows=ROWS, **kw):
    """Return (chars, colors): the ASCII portrait plus a source colour per cell.

    The glyph carries the shape and the fill carries the colour, sampled from the
    photo itself, so the hair, skin, shirt and tie keep roughly the hues they have
    in the original rather than being hand-picked.
    """
    lines = build(path, cols=cols, rows=rows, **kw)

    crop = kw.get("crop", (0.11, 0.05, 0.89, 1.0))
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    small = im.resize((cols, rows), Image.LANCZOS)
    px = np.asarray(small, dtype=np.float32)

    colors = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append(tuple(int(v) for v in px[r, c]))
        colors.append(row)
    return lines, colors


def write_portrait(path, out, **kw):
    import json
    chars, colors = build_colored(path, **kw)
    with open(out, "w") as f:
        json.dump({"chars": chars, "colors": colors}, f)
    return chars, colors
