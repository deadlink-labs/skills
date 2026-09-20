# Claude skills

Personal skills, kept here rather than inside any one project, because each of them is
useful across projects.

## Install on a machine

A skill is global when it sits in `~/.claude/skills/<name>/`. Symlink it, so the file that
runs is the one in this folder and an edit here is live everywhere:

```bash
ln -s /Volumes/AV/a-big-folder/projects/deadlink-labs/repos/skills/claude/<name> ~/.claude/skills/<name>
```

Check it with `/skills` in a session, or just ask for the thing the skill does — the
`description` in its frontmatter is what Claude matches against.

## What's here

| skill | does |
|---|---|
| [frame-screenshot](frame-screenshot/) | macOS-style framing for any image: rounded corners, drop shadow, transparent margins, optional aspect padding. Clipboard in and out (`-c`), a whole folder in place (`*_fi`, re-runnable), or the newest screenshot (`--last`). Shell function `frame-it` in `~/.zshrc`. Needs Pillow; numpy only for `--detect`. |

## Notes

- One folder per skill, `SKILL.md` at its root, code under `scripts/`.
- The `description` is the trigger. Write it as *when to use this*, with the words a person
  would actually say, not a summary of the implementation.
- This folder is deliberately **not** a git repo yet, like the rest of `repos/` that has not
  earned one.
