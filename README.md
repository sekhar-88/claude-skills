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

Use `~/.claude/skills/` instead of `.claude/skills/` to install it for every
project on the machine rather than just the current one.

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

The metrics are scripted (`scripts/measure.py`, no dependencies, degrades
gracefully when there is no git/docs tree/memory vault). The judgement is not:
the skill's core is sorting rules into *inferable* (a competent engineer would do
this anyway — cut it) and *not inferable* (a fact about this system that
contradicts what best practice suggests — keep it, in one line).
