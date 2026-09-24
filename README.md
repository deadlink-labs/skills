# Claude skills

Personal skills, kept here rather than inside any one project, because each of them is
useful across projects.

Each skill is its own repo, so each one can be public or private on its own. This repo is
just the list of the public ones.

## Install on a machine

A skill is global when it sits in `~/.claude/skills/<name>/`. Clone it straight there:

```bash
git clone https://github.com/deadlink-labs/<name> ~/.claude/skills/<name>
```

To work on a skill, clone it anywhere and symlink it instead, so the file that runs is the
one you edit and an edit is live everywhere:

```bash
# from the folder that holds the clone
ln -s "$(pwd)/<name>" ~/.claude/skills/<name>
```

Check it with `/skills` in a session, or just ask for the thing the skill does — the
`description` in its frontmatter is what Claude matches against.

## What's here

| skill | does |
|---|---|
| [Frame It!](https://github.com/deadlink-labs/frame-it) · `frame-it` | macOS-style framing for any image: rounded corners, drop shadow, transparent margins, optional aspect padding. Clipboard in and out (`-c`), a whole folder in place (`*_fi`, re-runnable), or the newest screenshot (`--last`). Shell function `frame-it` in `~/.zshrc`. Needs Pillow; numpy only for `--detect`. |

## Notes

- One repo per skill, named after the skill, with `SKILL.md` at its root and code under
  `scripts/`.
- The `description` is the trigger. Write it as *when to use this*, with the words a person
  would actually say, not a summary of the implementation.
