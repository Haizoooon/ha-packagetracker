"""Generate the Package Tracker icon/logo brand assets with Pillow."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "package_tracker" / "brand"
DOCS = ROOT / "docs"
BRAND.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

NAVY_TOP = (11, 31, 51)
NAVY_BOTTOM = (24, 70, 107)
TEAL = (45, 212, 191)
TEAL_DARK = (20, 160, 148)
WHITE = (247, 250, 253)
INK = (12, 33, 54)
MUTED = (99, 118, 137)
DARK_MUTED = (199, 210, 222)

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


def gradient(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        ratio = y / (size - 1)
        color = tuple(
            round(NAVY_TOP[i] * (1 - ratio) + NAVY_BOTTOM[i] * ratio)
            for i in range(3)
        )
        draw.line((0, y, size, y), fill=color)
    return image


def icon_master(size: int = 2048, dark: bool = False) -> Image.Image:
    base = gradient(size).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=255
    )
    base.putalpha(mask)
    draw = ImageDraw.Draw(base)

    # Soft route line behind the parcel.
    points = [
        (int(size * 0.16), int(size * 0.78)),
        (int(size * 0.28), int(size * 0.66)),
        (int(size * 0.40), int(size * 0.70)),
        (int(size * 0.52), int(size * 0.58)),
        (int(size * 0.66), int(size * 0.60)),
        (int(size * 0.79), int(size * 0.46)),
    ]
    draw.line(points, fill=(45, 212, 191, 75), width=int(size * 0.012), joint="curve")
    for index, point in enumerate(points):
        r = int(size * (0.012 if index % 2 else 0.017))
        draw.ellipse(
            (point[0] - r, point[1] - r, point[0] + r, point[1] + r),
            fill=(45, 212, 191, 150),
        )

    # Parcel drop shadow.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (
            int(size * 0.245),
            int(size * 0.48),
            int(size * 0.80),
            int(size * 0.83),
        ),
        radius=int(size * 0.035),
        fill=(0, 0, 0, 80),
    )
    base.alpha_composite(shadow.filter(__import__("PIL.ImageFilter").ImageFilter.GaussianBlur(int(size * 0.02))))

    # Front of the parcel.
    x0, x1 = int(size * 0.245), int(size * 0.76)
    y0, y1 = int(size * 0.47), int(size * 0.82)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=int(size * 0.03), fill=WHITE)
    # Top lid (perspective).
    draw.polygon(
        [
            (x0, y0),
            (int(size * 0.36), int(size * 0.33)),
            (int(size * 0.72), int(size * 0.40)),
            (x1, y0),
        ],
        fill=(255, 255, 255),
    )
    draw.line(
        [(int(size * 0.36), int(size * 0.33)), (int(size * 0.72), int(size * 0.40))],
        fill=(219, 231, 241),
        width=int(size * 0.008),
    )
    # Right-side shading.
    draw.polygon(
        [
            (x1, y0),
            (int(size * 0.72), int(size * 0.40)),
            (int(size * 0.72), int(size * 0.75)),
            (x1, y1),
        ],
        fill=(225, 236, 246),
    )
    # Tape.
    draw.rectangle(
        (int(size * 0.48), y0, int(size * 0.53), y1),
        fill=TEAL,
    )
    draw.polygon(
        [
            (int(size * 0.48), y0),
            (int(size * 0.505), int(size * 0.40)),
            (int(size * 0.55), int(size * 0.41)),
            (int(size * 0.53), y0),
        ],
        fill=TEAL_DARK,
    )

    # Location pin.
    pin_x, pin_y = int(size * 0.77), int(size * 0.24)
    pin_r = int(size * 0.095)
    draw.ellipse(
        (pin_x - pin_r, pin_y - pin_r, pin_x + pin_r, pin_y + pin_r),
        fill=TEAL,
        outline=NAVY_TOP,
        width=int(size * 0.012),
    )
    draw.polygon(
        [
            (pin_x - int(pin_r * 0.55), pin_y + int(pin_r * 0.55)),
            (pin_x + int(pin_r * 0.55), pin_y + int(pin_r * 0.55)),
            (pin_x, pin_y + int(pin_r * 1.45)),
        ],
        fill=TEAL,
    )
    inner = int(pin_r * 0.36)
    draw.ellipse(
        (pin_x - inner, pin_y - inner, pin_x + inner, pin_y + inner),
        fill=NAVY_TOP,
    )
    return base


def spaced_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    spacing: int,
) -> int:
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + spacing
    return x


def logo_master(size: tuple[int, int], dark: bool = False) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    icon_size = int(height * 0.54)
    icon = icon_master(icon_size)
    image.alpha_composite(icon, (int(height * 0.11), int(height * 0.23)))

    text_x = int(height * 0.11) + icon_size + int(height * 0.10)
    available = width - text_x - int(height * 0.07)
    package = "Package"
    tracker = "Tracker"
    font_size = int(height * 0.20)
    while font_size > int(height * 0.10):
        bold_big = ImageFont.truetype(FONT_BOLD, font_size)
        total = draw.textlength(package + " ", font=bold_big) + draw.textlength(
            tracker, font=bold_big
        )
        if total <= available:
            break
        font_size -= 4
    bold_big = ImageFont.truetype(FONT_BOLD, font_size)
    bold_tag = ImageFont.truetype(FONT_REGULAR, int(height * 0.052))
    text_y = int(height * 0.27)
    draw.text((text_x, text_y), package, font=bold_big, fill=(WHITE if dark else INK))
    offset = draw.textlength(package + " ", font=bold_big)
    draw.text((text_x + offset, text_y), tracker, font=bold_big, fill=TEAL)
    spaced_text(
        draw,
        (text_x + int(height * 0.012), int(height * 0.59)),
        "SMART PARCEL TRACKING",
        bold_tag,
        DARK_MUTED if dark else MUTED,
        int(height * 0.010),
    )
    return image


def save(image: Image.Image, path: Path, size: tuple[int, int]) -> None:
    image.resize(size, Image.Resampling.LANCZOS).save(path, "PNG", optimize=True)


icon = icon_master(2048)
save(icon, BRAND / "icon.png", (256, 256))
save(icon, BRAND / "icon@2x.png", (512, 512))
save(icon, BRAND / "dark_icon.png", (256, 256))
save(icon, BRAND / "dark_icon@2x.png", (512, 512))

logo = logo_master((2048, 1024))
save(logo, BRAND / "logo.png", (512, 256))
save(logo, BRAND / "logo@2x.png", (1024, 512))
dark_logo = logo_master((2048, 1024), dark=True)
save(dark_logo, BRAND / "dark_logo.png", (512, 256))
save(dark_logo, BRAND / "dark_logo@2x.png", (1024, 512))

# Documentation banner on a light surface.
banner = Image.new("RGBA", (1600, 700), (0, 0, 0, 0))
ImageDraw.Draw(banner).rounded_rectangle(
    (0, 0, 1599, 699), radius=70, fill=(245, 249, 252, 255)
)
banner.alpha_composite(logo_master((1400, 700)), (100, 0))
banner.save(DOCS / "logo.png", "PNG", optimize=True)
save(icon, DOCS / "icon.png", (256, 256))

print("Brand assets generated")
