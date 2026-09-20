#!/usr/bin/env python3
"""Frame an image like a macOS window screenshot: rounded corners, a soft drop
shadow, transparent margins.

macOS gives a window capture (Cmd+Shift+4, then Space) rounded corners and a
shadow for free. A region capture (Cmd+Shift+4 and drag), a crop, an export
from a tool, or a frame lifted out of a full-screen capture gets none of that,
and a hard-edged rectangle looks pasted onto a page. This adds the treatment
after the fact, to any image.

    python3 frame_shot.py -c                             # clipboard in, clipboard out
    python3 frame_shot.py --last                         # the newest screenshot on the Desktop
    python3 frame_shot.py shot.png                       # frame the whole image
    python3 frame_shot.py post/images/                   # a whole folder, in place, as *_fi.png
    python3 frame_shot.py *.png --out framed --aspect 16:9
    python3 frame_shot.py cap.png --detect 141721        # crop to a flat-coloured pane first
    python3 frame_shot.py shot.png --bg white            # flatten onto white instead of alpha

Writes <name>.png, plus <name>.webp unless --no-webp. Alpha is kept, so the
shadow composites onto whatever the page's background is.

With -c the framed image goes straight back to the clipboard, ready to paste
into a doc, a deck or a chat. Copy a screenshot with Cmd+Ctrl+Shift+4 (the
Ctrl is what sends it to the clipboard instead of a file).

Pillow is required. numpy is required only for --detect.
"""

import argparse
import glob
import os
import subprocess
import sys
import tempfile
import time

try:
    from PIL import Image, ImageColor, ImageDraw, ImageFilter
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install pillow")


IMAGE_EXTS = ("png", "jpg", "jpeg", "webp", "heic", "tif", "tiff", "bmp")


def _osa(*lines):
    cmd = ["osascript"]
    for ln in lines:
        cmd += ["-e", ln]
    return subprocess.run(cmd, capture_output=True, text=True)


def clipboard_read(path):
    """Write the clipboard's image to `path`. True if there was one."""
    r = _osa('set p to (the clipboard as \u00abclass PNGf\u00bb)',
             f'set f to open for access POSIX file "{path}" with write permission',
             "write p to f", "close access f")
    return r.returncode == 0 and os.path.exists(path)


def clipboard_write(path):
    r = _osa(f'set the clipboard to (read (POSIX file "{path}") as \u00abclass PNGf\u00bb)')
    return r.returncode == 0


def screenshot_dir():
    r = subprocess.run(["defaults", "read", "com.apple.screencapture", "location"],
                       capture_output=True, text=True)
    d = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "~/Desktop"
    return os.path.expanduser(d)


def images_in(folder):
    """Every image directly inside `folder`, name order. Not recursive."""
    files = []
    for ext in IMAGE_EXTS:
        files += glob.glob(os.path.join(folder, f"*.{ext}"))
        files += glob.glob(os.path.join(folder, f"*.{ext.upper()}"))
    return sorted(set(files))


def newest_image(folder, n=1):
    """The n most recent images in `folder`, newest first."""
    files = sorted(images_in(folder), key=os.path.getmtime, reverse=True)
    return files[:n]


def detect_box(im, bg, tol=2, frac=0.10):
    """Bounding box of the largest region painted a flat colour.

    Rows and columns that are at least `frac` background-coloured; the
    threshold drops stray matches elsewhere on the screen (a handful of
    pixels in a thumbnail or an icon) without touching content sitting on the
    background, which never covers a whole row of it.
    """
    try:
        import numpy as np
    except ImportError:
        sys.exit("--detect needs numpy: python3 -m pip install numpy")
    a = np.asarray(im.convert("RGB")).astype(int)
    m = (np.abs(a - np.array(bg)) <= tol).all(axis=2)
    cols = np.where(m.sum(axis=0) >= frac * m.shape[0])[0]
    rows = np.where(m.sum(axis=1) >= frac * m.shape[1])[0]
    if not len(cols) or not len(rows):
        return None
    return (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)


def pad_aspect(im, aspect):
    """Grow the canvas to `aspect` (w/h) with transparent margins, the image
    centred. Never shrinks, never crops."""
    w, h = im.size
    if w / h < aspect:
        nw, nh = round(h * aspect), h
    else:
        nw, nh = w, round(w / aspect)
    out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    out.paste(im, ((nw - w) // 2, (nh - h) // 2))
    return out


def frame(im, radius, blur, offset, alpha, scale):
    """Round the corners, add the shadow, return RGBA with transparent margins."""
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)),
                       Image.LANCZOS)
    w, h = im.size
    pad = blur * 2 + abs(offset)

    # The corner mask: an anti-aliased rounded rectangle drawn at 4x. Pillow's
    # rounded_rectangle aliases badly at 1x and the jaggies show against a
    # light page.
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1),
                                          radius=radius * 4, fill=255)
    mask = big.resize((w, h), Image.LANCZOS)

    # The shadow: the same silhouette, blurred, offset downwards. Padding is
    # 2x the blur so the falloff is never clipped at the canvas edge.
    shadow = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sil = Image.new("RGBA", (w, h), (0, 0, 0, round(255 * alpha)))
    shadow.paste(sil, (pad, pad + offset), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))

    out = shadow
    out.paste(im.convert("RGBA"), (pad, pad), mask)
    return out


def flatten(im, color):
    bg = Image.new("RGBA", im.size, ImageColor.getrgb(color) + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("images", nargs="*", help="image files to frame")
    ap.add_argument("-c", "--clipboard", action="store_true",
                    help="read the image from the clipboard and put the result "
                         "back on it, ready to paste")
    ap.add_argument("--last", nargs="?", type=int, const=1, metavar="N",
                    help="frame the N most recent images in the screenshot "
                         "folder (default 1)")
    ap.add_argument("--out", default="framed", help="output directory (default: ./framed)")
    ap.add_argument("--box", help="crop to L,T,R,B before framing")
    ap.add_argument("--detect", help="crop to the region painted this hex colour "
                    "first, e.g. 141721 (needs numpy)")
    ap.add_argument("--aspect", help="pad the finished image to W:H, e.g. 16:9")
    ap.add_argument("--bg", help="flatten onto this colour instead of keeping "
                    "alpha, e.g. white or '#f7f5f2'")
    ap.add_argument("--dpr", choices=["auto", "1", "2"], default="auto",
                    help="pixel density of the input; scales the corner and "
                    "shadow defaults (auto: 2 when the image is wider than 1400px)")
    ap.add_argument("--radius", type=int, help="corner radius in px (default 24 at 2x)")
    ap.add_argument("--blur", type=int, help="shadow blur in px (default 48 at 2x)")
    ap.add_argument("--offset", type=int, help="shadow y offset in px (default 24 at 2x)")
    ap.add_argument("--alpha", type=float, default=0.55, help="shadow opacity (default 0.55)")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="resize before framing, e.g. 0.5 to halve a 2x capture")
    ap.add_argument("--suffix", default="_fi",
                    help="appended to the name when the framed copy lands next "
                         "to its source (default _fi). Files already carrying "
                         "it are skipped, so a folder can be re-run safely.")
    ap.add_argument("--force", action="store_true",
                    help="re-frame sources whose framed copy already exists")
    ap.add_argument("--no-webp", action="store_true")
    a = ap.parse_args()

    fixed = tuple(int(v) for v in a.box.split(",")) if a.box else None
    if fixed and (len(fixed) != 4 or fixed[0] >= fixed[2] or fixed[1] >= fixed[3]):
        sys.exit(f"bad --box {a.box}; want L,T,R,B")
    detect = ImageColor.getrgb("#" + a.detect.lstrip("#")) if a.detect else None
    aspect = None
    if a.aspect:
        aw, ah = (float(v) for v in a.aspect.replace("/", ":").split(":"))
        aspect = aw / ah
    # A directory argument means "every image in it, framed in place". Each
    # entry carries the folder its output belongs in, so one run can mix a
    # folder, a loose file and the clipboard.
    images, skipped = [], 0
    for item in a.images:
        if os.path.isdir(item):
            found = images_in(item)
            if not found:
                sys.exit(f"{item}: no images in it")
            for f in found:
                stem = os.path.splitext(os.path.basename(f))[0]
                twin = os.path.join(item, stem + a.suffix + ".png")
                # Already framed, or already has its framed twin: leave it.
                if stem.endswith(a.suffix) or (os.path.exists(twin) and not a.force):
                    skipped += 1
                    continue
                images.append((f, item))
        else:
            images.append((item, None))
    tmp = None
    if a.clipboard:
        tmp = os.path.join(tempfile.mkdtemp(prefix="frameshot-"), "clipboard.png")
        if not clipboard_read(tmp):
            sys.exit("no image on the clipboard. Copy one first "
                     "(Cmd+Ctrl+Shift+4 screenshots straight to the clipboard).")
        images.append((tmp, None))
    if a.last:
        found = newest_image(screenshot_dir(), a.last)
        if not found:
            sys.exit(f"no images in {screenshot_dir()}")
        images += [(f, None) for f in found]
    if not images:
        if skipped:
            # Not an error: a re-run with nothing new is the normal case.
            print(f"  nothing to do: {skipped} image(s) already framed or "
                  f"already have a *{a.suffix} copy. --force redoes them.")
            return
        sys.exit("nothing to frame: pass a file or folder, -c for the "
                 "clipboard, or --last")
    if skipped:
        print(f"  skipping {skipped} already done (*{a.suffix} or has one)")

    # Clipboard in, clipboard out: the file is a by-product, so park it in the
    # screenshot folder under a name that sorts next to the original.
    if a.clipboard and not any(f in sys.argv for f in ("--out",)):
        a.out = screenshot_dir()

    # An explicit --out overrides everything; without one, images that came
    # from a folder stay in it and the rest go to the default out dir.
    explicit_out = "--out" in sys.argv

    for path, from_dir in images:
        im = Image.open(path)
        box = fixed
        if box is None and detect:
            box = detect_box(im, detect)
            if box is None:
                sys.exit(f"{path}: nothing painted #{a.detect}; pass --box instead")
        if box:
            if box[2] > im.width or box[3] > im.height:
                sys.exit(f"{path}: {im.size} is smaller than the box {box}")
            im = im.crop(box)

        dpr = 2 if (a.dpr == "auto" and im.width > 1400) else (1 if a.dpr == "auto" else int(a.dpr))
        radius = a.radius if a.radius is not None else 24 * dpr // 2
        blur = a.blur if a.blur is not None else 48 * dpr // 2
        offset = a.offset if a.offset is not None else 24 * dpr // 2

        out = frame(im, radius, blur, offset, a.alpha, a.scale)
        if aspect:
            out = pad_aspect(out, aspect)
        if a.bg:
            out = flatten(out, a.bg)

        # Where it lands: an explicit --out wins; a folder argument keeps its
        # images together; everything else goes to the default out dir.
        out_dir = a.out if explicit_out else (from_dir or a.out)
        os.makedirs(out_dir, exist_ok=True)

        stem = os.path.splitext(os.path.basename(path))[0]
        if path == tmp:
            stem = "framed-" + time.strftime("%Y-%m-%d-%H%M%S")
        elif os.path.abspath(out_dir) == os.path.abspath(os.path.dirname(path) or "."):
            stem += a.suffix           # never overwrite the source
        png = os.path.join(out_dir, stem + ".png")
        out.save(png, optimize=True)
        note = f" (crop {box})" if box else ""
        shown_in = os.path.basename(path) if from_dir else path
        shown_out = os.path.basename(png) if from_dir else png
        line = f"  {shown_in}{note} -> {shown_out} {out.size[0]}x{out.size[1]} @{dpr}x"
        if not a.no_webp and not a.clipboard:
            webp = os.path.join(out_dir, stem + ".webp")
            out.save(webp, quality=90, method=6)
            line += f", {stem}.webp {os.path.getsize(webp) // 1024}KB"
        if a.clipboard and path == tmp:
            line += " -> clipboard" if clipboard_write(png) else " (clipboard write FAILED)"
        print(line)


if __name__ == "__main__":
    sys.exit(main())
