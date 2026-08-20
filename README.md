# sekhar-skills

Claude Code skills, distributed as a plugin marketplace.

## Install (recommended)

In any project, from an interactive `claude` session:

```
/plugin marketplace add sekhar-88/claude-skills
/plugin install knowledge-base-audit@sekhar-skills
```

The marketplace is fetched from GitHub and cached under `~/.claude/plugins/`.
Re-run `/plugin marketplace update sekhar-skills` to pull later changes.

## Install without plugins

A skill is just a directory. To drop one into a single project:

```bash
git clone --depth 1 https://github.com/sekhar-88/claude-skills /tmp/sekhar-skills
mkdir -p .claude/skills
cp -R /tmp/sekhar-skills/plugins/knowledge-base-audit/skills/knowledge-base-audit .claude/skills/
```

Same thing in PowerShell:

```powershell
git clone --depth 1 https://github.com/sekhar-88/claude-skills "$env:TEMP\sekhar-skills"
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse "$env:TEMP\sekhar-skills\plugins\knowledge-base-audit\skills\knowledge-base-audit" .claude\skills\
```

Use `~/.claude/skills/` instead of `.claude/skills/` to install it for every
project on the machine rather than just the current one.

`measure.py` needs Python 3.6 or newer and no packages. Call it with whichever of
`python3`, `python` or `py -3` reaches an interpreter on your machine.

## Skills

### knowledge-base-audit

Audits and overhauls a project's agent knowledge base — `CLAUDE.md`, `AGENTS.md`,
`README.md`, the docs tree and the Claude memory vault.

```
/knowledge-base-audit report    # measure and report, change nothing
/knowledge-base-audit           # full overhaul, starting with that report
```

It measures context rent per turn, section-level rule density, **where commits
actually land versus what the guidance foregrounds**, duplication between files,
dead pointers, and memory notes that merely restate the docs. Then it restructures
the guidance file so it is preflight — the things an agent must know before
touching code — rather than a second copy of the documentation.

The metrics are scripted (`scripts/measure.py`, no dependencies). Anything it
cannot find, it names in the first line of the report, including the path it
probed for the memory vault, so a wrong path never reads as an absent file. The
judgement is not scripted: the skill's core is sorting rules into *inferable* (a
competent engineer would do this anyway, so cut it) and *not inferable* (a fact
about this system that contradicts what best practice suggests, so keep it, in
one line).
