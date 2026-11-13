"""Generate correctly shaped Bengali lyric bitmaps for the ESP32 OLED player.

Required packages:
    py -3.12 -m pip install pillow uharfbuzz freetype-py

Keep this file beside the project's `web` folder and Bengali Unicode .ttf font.
Output bitmaps are 128x64, monochrome, row-major, MSB-first (1024 bytes each).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import freetype
    import uharfbuzz as hb
    from PIL import Image, ImageChops, ImageDraw, ImageFont
except ImportError as exc:
    missing = getattr(exc, "name", "a required package")
    raise SystemExit(
        f"\nMissing Python package: {missing}\n"
        "Install the required packages in the Python version you use to run this script:\n"
        "  py -3.12 -m pip install --upgrade pillow uharfbuzz freetype-py\n"
        "Then run this script again.\n"
    ) from exc

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
BITMAP_DIR = WEB / "bitmaps"
MANIFEST_PATH = WEB / "manifest.json"

# Timestamps are seconds from the beginning of the song.
# These are the same lyric lines and timestamps from your original script.
LYRICS = [
    (32, "তুমি"),
    (35, "সামনে নেই"),
    (39, "তাও তুমি"),
    (43, "ভাসো"),
    (46, "মনের"),
    (50, "মাঝে"),
    (53, "লুকিয়ে"),
    (56, "একটুখানি হাসো"),
    (61, "স্বপ্নে আমার তোমার ছবি"),
    (66, "চুপটি করে আসে"),
    (69, "সকাল থেকে"),
    (71, "রাতের শেষে"),
    (73, "থাকো আমার পাশে"),
    (78, "তাতা তা"),
    (81, "তারারা"),
    (85, "তারারা"),
    (86, "রারা রারা"),
    (87, "রারা রারা"),
]

W, H = 128, 64
FONT_SIZE = 22
MIN_FONT_SIZE = 8
TEXT_MARGIN = 2
LINE_GAP = 2
MONO_THRESHOLD = 96  # Lower values keep more thin strokes on the tiny OLED.

PREFERRED_FONT_NAMES = (
    "Kalpana UNICODE.ttf",
    "Kalpana UNICODE(1).ttf",
    "Kalpana UNICODE (1).ttf",
    "Kalpana.ttf",
)


def _decode_name(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _use_unicode_charmap(face) -> None:
    """Select FreeType's Unicode charmap if it is available."""
    unicode_encoding = getattr(freetype, "FT_ENCODING_UNICODE", None)
    for charmap in getattr(face, "charmaps", []):
        if unicode_encoding is not None and charmap.encoding == unicode_encoding:
            face.set_charmap(charmap)
            return


def _supports_bengali_font(path: Path) -> bool:
    try:
        face = freetype.Face(str(path))
        _use_unicode_charmap(face)
        # Check basic consonants and vowel signs used in the supplied lyrics.
        return all(face.get_char_index(ord(ch)) != 0 for ch in "তুমিাসনেক")
    except Exception:
        return False


def find_font() -> Path:
    for name in PREFERRED_FONT_NAMES:
        candidate = ROOT / name
        if candidate.is_file():
            if not _supports_bengali_font(candidate):
                raise SystemExit(
                    f"Found {candidate.name}, but it does not appear to contain the needed "
                    "Unicode Bengali glyphs. Use the uploaded 'Kalpana UNICODE' font."
                )
            return candidate

    ttf_files = list(ROOT.glob("*.ttf")) + list(ROOT.glob("*.TTF"))
    valid = [p for p in ttf_files if _supports_bengali_font(p)]
    kalpana = [p for p in valid if "kalpana" in p.name.lower()]
    if len(kalpana) == 1:
        return kalpana[0]
    if len(valid) == 1:
        return valid[0]
    if len(valid) > 1:
        names = "\n  ".join(p.name for p in valid)
        raise SystemExit(
            "More than one Bengali Unicode font was found. Rename the font you want to use "
            "to 'Kalpana.ttf' and run again. Found:\n  " + names
        )
    raise SystemExit(
        "Could not find a Bengali Unicode .ttf font beside this script.\n"
        "Copy your uploaded 'Kalpana UNICODE' font into this folder and rename it to "
        "'Kalpana.ttf'."
    )


def make_hb_font(font_path: Path):
    font_bytes = font_path.read_bytes()
    hb_face = hb.Face(font_bytes)
    hb_font = hb.Font(hb_face)
    upem = hb_face.upem
    if not upem:
        raise SystemExit(f"The font {font_path.name} has an invalid units-per-em value.")
    hb_font.scale = (upem, upem)
    hb.ot_font_set_funcs(hb_font)
    return hb_font, upem


def bitmap_to_image(bitmap) -> Image.Image:
    """Convert a FreeType glyph bitmap to Pillow grayscale, respecting pitch."""
    width = int(bitmap.width)
    rows = int(bitmap.rows)
    if width <= 0 or rows <= 0:
        return Image.new("L", (max(0, width), max(0, rows)), 0)

    pitch = int(bitmap.pitch)
    stride = abs(pitch)
    data = bytes(bitmap.buffer)
    pixel_mode = int(bitmap.pixel_mode)
    output = bytearray(width * rows)

    if pixel_mode == int(freetype.FT_PIXEL_MODE_GRAY):
        num_grays = int(getattr(bitmap, "num_grays", 256)) or 256
        for y in range(rows):
            src_y = y if pitch >= 0 else rows - 1 - y
            src_start = src_y * stride
            row = data[src_start:src_start + width]
            if num_grays != 256:
                denom = max(1, num_grays - 1)
                row = bytes(min(255, (v * 255 + denom // 2) // denom) for v in row)
            output[y * width:(y + 1) * width] = row
    elif pixel_mode == int(freetype.FT_PIXEL_MODE_MONO):
        bytes_per_row = (width + 7) // 8
        for y in range(rows):
            src_y = y if pitch >= 0 else rows - 1 - y
            row_start = src_y * stride
            for x in range(width):
                byte_value = data[row_start + x // 8]
                output[y * width + x] = 255 if byte_value & (0x80 >> (x % 8)) else 0
        # `bytes_per_row` documents the logical mono row width; FreeType may pad it.
        _ = bytes_per_row
    else:
        raise RuntimeError(
            f"Unsupported FreeType bitmap pixel mode {pixel_mode}. "
            "Expected grayscale or monochrome glyphs."
        )

    return Image.frombytes("L", (width, rows), bytes(output))


def layout_line(text: str, size: int, hb_font, upem: int, ft_face):
    """Shape a line with HarfBuzz, then rasterize those exact glyph IDs via FreeType."""
    ft_face.set_pixel_sizes(0, size)

    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction = "ltr"
    buffer.script = "Beng"
    buffer.language = "bn"
    hb.shape(hb_font, buffer)

    factor = size / float(upem)
    pen_x = 0.0
    glyphs = []
    min_x = min_y = None
    max_x = max_y = None

    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
        glyph_id = int(info.codepoint)
        ft_face.load_glyph(
            glyph_id,
            freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL,
        )
        slot = ft_face.glyph
        mask = bitmap_to_image(slot.bitmap)

        gx = round(pen_x + position.x_offset * factor) + int(slot.bitmap_left)
        gy = round(-position.y_offset * factor) - int(slot.bitmap_top)

        if mask.width and mask.height:
            glyphs.append((mask, gx, gy))
            min_x = gx if min_x is None else min(min_x, gx)
            min_y = gy if min_y is None else min(min_y, gy)
            max_x = gx + mask.width if max_x is None else max(max_x, gx + mask.width)
            max_y = gy + mask.height if max_y is None else max(max_y, gy + mask.height)

        pen_x += position.x_advance * factor

    if min_x is None:
        # E.g. a line containing only spaces; not expected in this lyric set.
        return {"glyphs": [], "min_x": 0, "max_x": max(1, round(pen_x)),
                "min_y": -size // 2, "max_y": size // 2}

    return {
        "glyphs": glyphs,
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
    }


def line_width(line: str, size: int, hb_font, upem: int, ft_face) -> int:
    layout = layout_line(line, size, hb_font, upem, ft_face)
    return int(layout["max_x"] - layout["min_x"])


def wrap_text(text: str, size: int, hb_font, upem: int, ft_face, max_width: int):
    words = text.split()
    if not words:
        return [text]

    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if current and line_width(candidate, size, hb_font, upem, ft_face) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_text(text: str, out_path: Path, hb_font, upem: int, ft_face) -> Image.Image:
    max_width = W - 2 * TEXT_MARGIN
    size = FONT_SIZE
    chosen_layouts = None

    while size >= MIN_FONT_SIZE:
        lines = wrap_text(text, size, hb_font, upem, ft_face, max_width)
        layouts = [layout_line(line, size, hb_font, upem, ft_face) for line in lines]
        widths = [entry["max_x"] - entry["min_x"] for entry in layouts]
        heights = [entry["max_y"] - entry["min_y"] for entry in layouts]
        total_height = sum(heights) + max(0, len(heights) - 1) * LINE_GAP
        if all(width <= max_width for width in widths) and total_height <= H - 2:
            chosen_layouts = layouts
            break
        size -= 1

    if chosen_layouts is None:
        raise RuntimeError(
            f"Lyric will not fit the OLED even at {MIN_FONT_SIZE}px: {text!r}. "
            "Try shortening that lyric line."
        )

    heights = [entry["max_y"] - entry["min_y"] for entry in chosen_layouts]
    total_height = sum(heights) + max(0, len(heights) - 1) * LINE_GAP
    top = max(0, (H - total_height) // 2)
    canvas = Image.new("L", (W, H), 0)

    for layout, height in zip(chosen_layouts, heights):
        ink_width = layout["max_x"] - layout["min_x"]
        x_origin = (W - ink_width) // 2 - layout["min_x"]
        baseline_y = top - layout["min_y"]

        for mask, gx, gy in layout["glyphs"]:
            px = x_origin + gx
            py = baseline_y + gy
            layer = Image.new("L", (W, H), 0)
            layer.paste(mask, (px, py))
            canvas = ImageChops.lighter(canvas, layer)

        top += height + LINE_GAP

    # Convert antialiased glyph strokes to crisp pixels for the monochrome OLED.
    binary = canvas.point(lambda value: 255 if value >= MONO_THRESHOLD else 0).convert("1")
    packed = bytearray()
    pixels = binary.load()
    for y in range(H):
        for byte_x in range(W // 8):
            value = 0
            for bit in range(8):
                if pixels[byte_x * 8 + bit, y]:
                    value |= 0x80 >> bit
            packed.append(value)

    if len(packed) != 1024:
        raise AssertionError(f"Expected 1024 bytes; produced {len(packed)}.")
    out_path.write_bytes(packed)
    return binary.convert("L")


def make_preview(images):
    """Save a contact sheet so the generated glyph placement can be checked on PC."""
    scale = 3
    columns = 3
    rows = (len(images) + columns - 1) // columns
    pad = 8
    tile_w, tile_h = W * scale, H * scale
    sheet = Image.new("RGB", (columns * tile_w + (columns + 1) * pad,
                               rows * (tile_h + 24) + (rows + 1) * pad), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        label_font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        label_font = ImageFont.load_default()

    for idx, (seconds, text, image) in enumerate(images):
        r, c = divmod(idx, columns)
        x = pad + c * (tile_w + pad)
        y = pad + r * (tile_h + 24 + pad)
        enlarged = image.resize((tile_w, tile_h), Image.Resampling.NEAREST)
        sheet.paste(enlarged.convert("RGB"), (x, y))
        draw.rectangle((x, y, x + tile_w - 1, y + tile_h - 1), outline=(100, 100, 100))
        draw.text((x, y + tile_h + 3), f"{idx:03d}  @ {seconds}s", font=label_font, fill=(235, 235, 235))

    preview_path = ROOT / "lyric_preview.png"
    sheet.save(preview_path)
    return preview_path


def main() -> None:
    if not WEB.is_dir():
        raise SystemExit(
            f"Could not find the project's 'web' folder at:\n  {WEB}\n\n"
            "Put this script in the BitmapLyricsPlayer project folder beside 'web', "
            "then run it again."
        )

    font_path = find_font()
    print(f"Using Bengali Unicode font: {font_path.name}")

    ft_face = freetype.Face(str(font_path))
    _use_unicode_charmap(ft_face)
    hb_font, upem = make_hb_font(font_path)

    BITMAP_DIR.mkdir(parents=True, exist_ok=True)
    preview_images = []

    for idx, (seconds, text) in enumerate(LYRICS):
        out_path = BITMAP_DIR / f"{idx:03d}.bin"
        image = render_text(text, out_path, hb_font, upem, ft_face)
        preview_images.append((seconds, text, image))
        print(f"Created {out_path.name}  ({seconds}s): {text}")

    # Keep existing manifest fields (such as the audio path) where possible.
    if MANIFEST_PATH.is_file():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                manifest = {}
        except (json.JSONDecodeError, OSError):
            manifest = {}
    else:
        manifest = {}

    manifest.setdefault("audio", "/songs/song.mp3")
    manifest["lyrics"] = [
        {"time": seconds, "image": f"/bitmaps/{idx:03d}.bin"}
        for idx, (seconds, _text) in enumerate(LYRICS)
    ]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    preview_path = make_preview(preview_images)
    print("\nDone.")
    print(f"Generated {len(LYRICS)} bitmap files, each exactly 1024 bytes.")
    print(f"Updated: {MANIFEST_PATH}")
    print(f"Preview: {preview_path}")
    print("Check lyric_preview.png before testing on the ESP32.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
