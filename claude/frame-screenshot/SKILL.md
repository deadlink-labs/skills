---
name: frame-screenshot
description: Frame an image like a macOS window screenshot — rounded corners, a soft drop shadow, transparent margins, optional 16:9 padding. Use when a screenshot, crop, chart, UI capture or exported image is going onto a web page, a product listing, a slide or a thumbnail and needs to sit on the background instead of looking pasted on; when the user says "add a shadow", "make it look like a Mac screenshot", "frame this", "round the corners"; or when preparing captures for a post, a store listing or a README.
---

# Frame a screenshot the way macOS does

macOS gives a **window** capture (Cmd+Shift+4, then Space) rounded corners and a shadow for
free. Everything else arrives as a hard-edged rectangle: a region capture, a crop out of a
full-screen frame, an export from a tool, an image someone sent. On a light page a hard edge
reads as pasted on, and a dark image with a hard edge reads as a hole. This adds the
treatment after the fact.

## The usual request: "frame this"

Most of the time the user has an image in hand and wants it framed with no fuss. Pick the
input that matches how it reached you:

| the image is | run |
|---|---|
| **on the clipboard** (they copied it, or shot it with Cmd+Ctrl+Shift+4) | `python3 scripts/frame_shot.py -c` |
| **the screenshot they just took** (a file on the Desktop) | `python3 scripts/frame_shot.py --last` |
| **a file they named or dropped as a path** | `python3 scripts/frame_shot.py <path>` |
| **a folder of them** (a blog post's images, say) | `python3 scripts/frame_shot.py <folder>` |
| **pasted into the conversation as an attachment** | you cannot reach those pixels — see below |

`-c` puts the framed image **straight back on the clipboard**, so the next thing they do is
paste it wherever it was going. It also drops a `framed-<timestamp>.png` in the screenshot
folder as a by-product.

**An image attached to the conversation is not a file you can process.** It arrives as pixels
in the transcript; there is no path, and re-encoding what you can see would be a lossy
imitation, not their image. Say so plainly and offer the clipboard: *copy it (Cmd+C on the
file, or Cmd+Ctrl+Shift+4 to shoot straight to the clipboard) and say "frame it"*. One extra
keystroke for them, full fidelity, and the result lands back on the clipboard.

Default output is `./framed/`, as PNG plus WebP. Alpha is kept, so the shadow composites onto
whatever colour the page is.

## A folder of images for a post

Point it at the folder. Every image in it is framed **in place**, next to its original, with
`_fi` on the name — `diagram.png` gives `diagram_fi.png` and `diagram_fi.webp`. Originals are
never touched, so the post can keep referencing them until the new ones are wired in.

```bash
python3 scripts/frame_shot.py content/posts/my-post/images/
```

**It is safe to re-run, and that is the point.** An image is skipped when it already ends in
`_fi`, and also when its `_fi` twin already exists. So the loop is: drop new crops into the
folder, run it again, only the new ones are processed. The run reports how many it skipped.
`--force` redoes them anyway; `--suffix` changes `_fi` to something else.

Not recursive: one folder per run, by design, so a stray `assets/` full of logos two levels
down never gets framed by accident.

## When it is going somewhere specific, decide these three things

| question | answer |
|---|---|
| Is the whole image the thing? | Yes → no crop flag. No → `--box L,T,R,B`, or `--detect <hex>` when the region is painted one flat colour. |
| Where is it going? | A page that may be light or dark → keep alpha (default). A fixed background → `--bg white` or `--bg '#f7f5f2'` bakes it in. Video or a 16:9 slot → add `--aspect 16:9`. |
| What density is the file? | Retina captures (wider than ~1400px) get 2x corners and shadow automatically. Override with `--dpr 1` or `--dpr 2` if the guess is wrong — a 1600px-wide 1x export would otherwise get corners twice as round as they should be. |

## The flags

| flag | what it does |
|---|---|
| `-c`, `--clipboard` | read the image from the clipboard, put the framed result back on it |
| `--last [N]` | frame the N newest images in the macOS screenshot folder (default 1, newest first) |
| `<folder>` | frame every unframed image directly inside it, in place, suffixed `_fi` |
| `--out DIR` | output directory, created if missing. Overrides the in-place rule for a folder. (default `./framed`; for `-c`, the screenshot folder) |
| `--suffix S` | the in-place suffix (default `_fi`) |
| `--force` | re-frame sources whose framed copy already exists |
| `--box L,T,R,B` | crop before framing, in pixels of the source |
| `--detect HEX` | crop to the bounding box of everything painted that colour — for lifting one flat-background pane (an app's canvas, a chart area) out of a full-screen capture. Needs numpy. |
| `--aspect W:H` | **pads** the finished image to that ratio with transparent margins, centred. Never crops. |
| `--bg COLOR` | flatten onto a solid colour; drops the alpha |
| `--radius --blur --offset --alpha` | the look. Defaults are 24 / 48 / 24 px at 2x and 0.55 opacity. |
| `--scale` | resize before framing (`0.5` turns a 2x capture into a 1x asset) |
| `--no-webp` | PNG only |

## Things that went wrong the first time

- **Trimming to an aspect ratio cuts the content.** The first version cropped to reach 16:9 and
  took an app's legend and logo off the left edge. Padding is right: the ratio is a container,
  not a lens. That is why `--aspect` only ever grows the canvas.
- **Check the crop on the first file before batching.** The tool prints the box it used on
  every line. Look at one output, then run the rest.
- **`--detect` follows the layout, which is a feature and a trap.** Hide a sidebar and the pane
  gets wider, so the same command gives a different crop on captures taken minutes apart.
  Batch captures that must match, or pass `--box`.
- **Corners alias at 1x.** The mask is drawn at 4x and downsampled for this reason; do not
  "simplify" that away.
- **The shadow needs room.** Margins are 2x the blur, so a blur of 48 adds ~96px of transparent
  padding on each side. That is correct — the image is meant to be placed with its margins, not
  trimmed to the visible edge.

- **A file is never overwritten by its own framed copy.** Landing in the source folder means
  the `_fi` suffix, always.
- **Re-running a folder used to redo everything.** Skipping only names ending in `_fi` is not
  enough — the *sources* are still there and still match. It has to skip a source whose `_fi`
  twin already exists, or every run reprocesses the whole post.

## Doing it without Claude

For a daily habit, a shell alias beats a conversation. Add to `~/.zshrc`:

```bash
frame-it() {
  local s=~/.claude/skills/frame-screenshot/scripts/frame_shot.py
  if [ $# -eq 0 ]; then python3 "$s" -c; else python3 "$s" "$@"; fi
}
```

Then `frame-it` on its own is clipboard in and clipboard out, and `frame-it ./images` does a
folder. **If that function is in the user's shell, point them at `frame-it`** rather than
running the script through a tool call: it is faster for them and costs no tokens.

## Capturing in the first place

This skill frames an image that already exists. To take the capture on macOS:

| want | do |
|---|---|
| one window, shadow included | `screencapture -w shot.png` — already framed, no need for this skill |
| a window without the shadow | `screencapture -o -w shot.png`, then frame it here |
| a region straight to the clipboard | Cmd+Ctrl+Shift+4, then `-c` |
| a region | `screencapture -R x,y,w,h shot.png`, or Cmd+Shift+4 |
| the whole screen | `screencapture -x shot.png`, then `--box` or `--detect` |
