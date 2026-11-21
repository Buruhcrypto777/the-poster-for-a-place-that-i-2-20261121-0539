"""VELMORA - a travel poster for a place that isn't there.

Draws a dusk poster for Velmora, a cliff town of amber glass above a
violet sea, using pure Python stdlib only. Encodes the PNG by hand
(struct + zlib), so the program runs offline with no fonts, no image
libraries and no network access.

Output: one PNG, 1024x768, written to $OUTPUT_DIR/entry.png
(default /output/entry.png).
"""

import os
import struct
import zlib

W = 1024
H = 768
OUT_NAME = "entry.png"

# ---------------------------------------------------------------- palette
# A small, purposeful dusk palette: deep violet sky, amber light,
# cream type, dark silhouettes.
SKY_TOP = (26, 16, 54)        # deep indigo-violet
SKY_MID = (91, 42, 110)       # violet
SKY_LOW = (214, 110, 84)      # ember rose above the horizon
HORIZON = (245, 166, 35)      # amber glow at the horizon line
SUN = (255, 196, 107)         # low sun
SUN_CORE = (255, 232, 170)
SEA = (59, 42, 107)           # violet sea
SEA_DARK = (38, 26, 74)
SEA_LIGHT = (122, 74, 140)    # lit water near the sun path
CLIFF = (22, 13, 44)          # near-black violet silhouette
CLIFF_FAR = (44, 26, 76)      # distant cliff, slightly lighter
GLASS = (245, 166, 35)        # amber glass towers
GLASS_DARK = (196, 110, 28)
GLASS_EDGE = (255, 214, 130)
WINDOW = (255, 243, 214)      # lit windows
CREAM = (255, 243, 214)       # poster type
TYPE_SHADOW = (26, 16, 54)
FOREGROUND = (16, 9, 32)

HORIZON_Y = 470
SEA_BOTTOM = 648

# ---------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def px(x, y):
    return (y * W + x) * 3


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = px(x, y)
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def blend_px(x, y, color, alpha):
    """Paint color over the pixel with alpha 0..1."""
    if 0 <= x < W and 0 <= y < H and alpha > 0:
        if alpha > 1:
            alpha = 1
        i = px(x, y)
        buf[i] = int(buf[i] * (1 - alpha) + color[0] * alpha)
        buf[i + 1] = int(buf[i + 1] * (1 - alpha) + color[1] * alpha)
        buf[i + 2] = int(buf[i + 2] * (1 - alpha) + color[2] * alpha)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fill_rect(x0, y0, x1, y1, color):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    for y in range(y0, y1):
        base = y * W * 3
        for x in range(x0, x1):
            i = base + x * 3
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]


def draw_line(x0, y0, x1, y1, color, width=1):
    """Bresenham line, with a square brush of the given width."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    half = width // 2
    while True:
        fill_rect(x - half, y - half, x + half + 1, y + half + 1, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_circle(cx, cy, r, color):
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        half = int((r * r - dy * dy) ** 0.5)
        fill_rect(cx - half, y, cx + half + 1, y + 1, color)


def glow_circle(cx, cy, r, color, max_alpha):
    """Soft radial glow: concentric rings fading outwards."""
    steps = 24
    for k in range(steps, 0, -1):
        rr = int(r * k / steps)
        alpha = max_alpha * (1 - k / steps) ** 2
        for y in range(cy - rr, cy + rr + 1):
            dy = y - cy
            half2 = rr * rr - dy * dy
            if half2 < 0:
                continue
            half = int(half2 ** 0.5)
            for x in range(cx - half, cx + half + 1):
                blend_px(x, y, color, alpha)


def fill_polygon(points, color):
    """Scanline polygon fill for a simple (non self-intersecting) polygon."""
    ys = [p[1] for p in points]
    y_min = max(0, min(ys))
    y_max = min(H - 1, max(ys))
    n = len(points)
    for y in range(y_min, y_max + 1):
        xs = []
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0 = int(xs[k])
            x1 = int(xs[k + 1])
            fill_rect(x0, y, x1 + 1, y + 1, color)


# ---------------------------------------------------------------- bitmap font
# Tiny 5x7 bitmap font, defined by hand. Only the letters the poster
# needs are included; each glyph is 7 rows of 5 bits.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "V": ["10001", "10001", "10001", "01010", "01010", "00100", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
}


def text_width(text, scale):
    """Width in pixels of text rendered at the given scale."""
    return len(text) * 6 * scale - scale


def draw_text(text, x, y, scale, color):
    """Draw text with the bitmap font; (x, y) is the top-left corner."""
    cx = x
    for ch in text:
        if ch == " ":
            cx += 6 * scale
            continue
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              cx + (col + 1) * scale,
                              y + (row + 1) * scale, color)
        cx += 6 * scale


# ---------------------------------------------------------------- scene
def paint_sky():
    """Dusk gradient: deep violet at the top, ember amber at the horizon."""
    for y in range(0, HORIZON_Y):
        t = y / HORIZON_Y
        if t < 0.55:
            color = lerp(SKY_TOP, SKY_MID, t / 0.55)
        else:
            color = lerp(SKY_MID, SKY_LOW, (t - 0.55) / 0.45)
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]
    # Thin amber band right at the horizon.
    for y in range(HORIZON_Y - 6, HORIZON_Y):
        t = (y - (HORIZON_Y - 6)) / 6
        color = lerp(SKY_LOW, HORIZON, t)
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]


def paint_sun():
    """Low sun, half-sunk toward the horizon, with a soft glow."""
    cx, cy, r = 668, 448, 74
    glow_circle(cx, cy, 210, HORIZON, 0.55)
    fill_circle(cx, cy, r, SUN)
    fill_circle(cx, cy, int(r * 0.62), SUN_CORE)
    # A few pale clouds catching the light: clusters of soft circles.
    for (ccx, ccy, cr) in [(180, 214, 16), (240, 232, 12),
                           (830, 176, 14), (884, 200, 10)]:
        cloud = lerp(SKY_MID, SUN, 0.35)
        fill_circle(ccx - cr, ccy, cr, cloud)
        fill_circle(ccx, ccy - cr // 2, cr, cloud)
        fill_circle(ccx + cr, ccy, cr, cloud)


def paint_sea():
    """Violet sea with an amber light-path under the sun."""
    for y in range(HORIZON_Y, SEA_BOTTOM):
        t = (y - HORIZON_Y) / (SEA_BOTTOM - HORIZON_Y)
        color = lerp(SEA_LIGHT, SEA_DARK, t)
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]
    # Shimmering light path beneath the sun.
    for row in range(0, 26):
        y = HORIZON_Y + 8 + row * 6
        spread = 46 + row * 7
        cx = 668
        for x in range(cx - spread, cx + spread + 1):
            d = abs(x - cx) / spread
            alpha = 0.55 * (1 - d) * (1 - row / 30)
            blend_px(x, y, SUN, alpha)
            blend_px(x, y + 1, SUN, alpha * 0.7)
    # Gentle wave strokes.
    for k in range(9):
        y = HORIZON_Y + 26 + k * 18
        x0 = 60 + (k * 97) % 700
        draw_line(x0, y, x0 + 70, y, lerp(SEA, CREAM, 0.35), 2)


def paint_cliffs_and_town():
    """Distant headland, the glass town on its promontory, near cliffs."""
    # Far headland on the right, softened by dusk haze.
    fill_polygon([(760, HORIZON_Y), (1024, HORIZON_Y), (1024, 430),
                  (940, 408), (860, 424), (800, 442)], CLIFF_FAR)
    # The promontory the town stands on, grounded down to the shore.
    fill_polygon([(330, HORIZON_Y), (700, HORIZON_Y), (690, 600),
                  (640, SEA_BOTTOM), (400, SEA_BOTTOM), (350, 600)], CLIFF)
    # Amber glass towers, tallest in the middle, catching the last sun.
    towers = [
        (352, 400, 44, 66), (402, 372, 52, 94), (460, 330, 56, 136),
        (522, 306, 60, 160), (588, 344, 52, 122), (646, 388, 40, 78),
    ]
    for (tx, top, tw, th) in towers:
        base = HORIZON_Y + 6
        fill_rect(tx, top, tx + tw, base, GLASS)
        fill_rect(tx, top, tx + 4, base, GLASS_EDGE)
        fill_rect(tx + tw - 4, top, tx + tw, base, GLASS_DARK)
        # Pointed glass roof.
        fill_polygon([(tx, top), (tx + tw, top),
                      (tx + tw // 2, top - 22)], GLASS_DARK)
        # Lit windows in a small grid.
        for wy in range(top + 18, base - 14, 26):
            for wx in range(tx + 10, tx + tw - 8, 16):
                fill_rect(wx, wy, wx + 7, wy + 11, WINDOW)
    # Near cliffs framing the scene on both sides.
    fill_polygon([(0, HORIZON_Y), (150, HORIZON_Y), (210, 560),
                  (120, SEA_BOTTOM), (0, SEA_BOTTOM)], CLIFF)
    fill_polygon([(1024, HORIZON_Y), (900, HORIZON_Y), (836, 560),
                  (920, SEA_BOTTOM), (1024, SEA_BOTTOM)], CLIFF)
    # A lone glass spire on the left cliff, echoing the town.
    fill_polygon([(96, 470), (118, 470), (107, 396)], GLASS_DARK)
    fill_circle(107, 398, 7, WINDOW)


def paint_foreground():
    """Dark foreground shore with rocks and a few pale dune grasses."""
    fill_polygon([(0, SEA_BOTTOM), (1024, SEA_BOTTOM), (1024, H),
                  (0, H)], FOREGROUND)
    fill_circle(120, 700, 46, CLIFF)
    fill_circle(210, 716, 30, CLIFF)
    fill_circle(880, 706, 52, CLIFF)
    fill_circle(790, 722, 28, CLIFF)


def paint_birds():
    """A few distant birds above the sea, drawn as small strokes."""
    for (bx, by, s) in [(300, 300, 12), (340, 282, 9), (760, 250, 11),
                        (800, 272, 8)]:
        draw_line(bx - s, by, bx, by - 6, CREAM, 2)
        draw_line(bx, by - 6, bx + s, by, CREAM, 2)


def paint_type():
    """The place name, large at the top, with a short tagline beneath."""
    name = "VELMORA"
    scale = 15
    tw = text_width(name, scale)
    x = (W - tw) // 2
    y = 56
    # Soft shadow so the letters sit on the sky.
    draw_text(name, x + 5, y + 6, scale, TYPE_SHADOW)
    draw_text(name, x, y, scale, CREAM)
    # Amber rule under the name.
    fill_rect(x + 20, y + 7 * scale + 18, x + tw - 20,
              y + 7 * scale + 24, GLASS)
    tagline = "WHERE LIGHT LIVES"
    tscale = 5
    ttw = text_width(tagline, tscale)
    tx = (W - ttw) // 2
    ty = y + 7 * scale + 44
    draw_text(tagline, tx + 2, ty + 2, tscale, TYPE_SHADOW)
    draw_text(tagline, tx, ty, tscale, GLASS_EDGE)


def paint_frame():
    """A thin cream frame, like a printed poster border."""
    fill_rect(0, 0, W, 10, CREAM)
    fill_rect(0, H - 10, W, H, CREAM)
    fill_rect(0, 0, 10, H, CREAM)
    fill_rect(W - 10, 0, W, H, CREAM)


# ---------------------------------------------------------------- PNG encode
def png_chunk(kind, data):
    chunk = struct.pack(">I", len(data)) + kind + data
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return chunk + struct.pack(">I", crc)


def encode_png():
    """Encode the RGB buffer as a PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        start = y * W * 3
        raw += buf[start:start + W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += png_chunk(b"IEND", b"")
    return png


def main():
    paint_sky()
    paint_sun()
    paint_sea()
    paint_cliffs_and_town()
    paint_foreground()
    paint_birds()
    paint_type()
    paint_frame()
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "wb") as f:
        f.write(encode_png())
    print("wrote", path)


if __name__ == "__main__":
    main()
